"""API 合同测试：/api/entities/*。"""
from fastapi.testclient import TestClient

LI_BAI = "p_li_bai"


def test_entities_list_persons(client: TestClient):
    """/api/entities?type=Person：列表非空，每项有 id/type 且 type==Person。"""
    r = client.get("/api/entities", params={"type": "Person", "limit": 50})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["total"] > 0
    assert isinstance(body["items"], list) and len(body["items"]) > 0
    for it in body["items"]:
        assert it["id"]
        assert it["type"] == "Person"


def test_entity_get_known(client: TestClient):
    """/api/entities/{id}：已知 id p_li_bai 返回李白。"""
    r = client.get(f"/api/entities/{LI_BAI}")
    assert r.status_code == 200, r.text
    e = r.json()
    assert e["id"] == LI_BAI
    assert e["type"] == "Person"
    assert e["name"] == "李白"


def test_entity_get_404(client: TestClient):
    """/api/entities/{id}：不存在的 id 返回 404。"""
    r = client.get("/api/entities/p_does_not_exist_xyz")
    assert r.status_code == 404


def test_core_march_routes_are_serialized_with_verified_legs(client: TestClient):
    """核心路线必须完整经 API 返回，且每段端点与出处不可丢失。"""
    expected = {
        "e_an_lushan_rebellion": [
            ("pl_youzhou", "pl_luoyang_sui", None),
            ("pl_luoyang_sui", "pl_chang_an", None),
        ],
        "b_shanhai_guan": [("pl_shenyang_qing", "pl_shanhaiguan", "k_qing")],
        "e_jingkang_zhibian": [
            ("pl_yunzhou", "pl_taiyuan", "k_jin"),
            ("pl_beijing_ylcj", "pl_kaifeng", "k_jin"),
        ],
        "e_sui_mie_chen": [("pl_caishiji", "pl_jianye", "k_sui")],
        "e_huangchao_zhan_changan": [("pl_luoyang_sui", "pl_chang_an", None)],
        "b_song_nantang": [
            ("pl_jiangling", "pl_caishiji", None),
            ("pl_caishiji", "pl_jinling", None),
        ],
        "b_yashan": [("pl_cbdb_100447", "pl_yashan2", None)],
    }

    for entity_id, legs in expected.items():
        response = client.get(f"/api/entities/{entity_id}")
        assert response.status_code == 200, response.text
        march = response.json().get("march")
        assert march and len(march) == len(legs)
        assert [
            (leg["from"], leg["to"], leg.get("side")) for leg in march
        ] == legs
        assert all("《" in leg.get("note", "") for leg in march)

    parent_response = client.get("/api/entities/e_huangchao_qiyi")
    assert parent_response.status_code == 200, parent_response.text
    assert not parent_response.json().get("march"), "父事件不得与880年具体阶段重复挂载路线"


def test_entity_neighbors(client: TestClient):
    """/api/entities/{id}/neighbors?depth=1：结构含 root/depth/nodes，root 指向自身。"""
    r = client.get(f"/api/entities/{LI_BAI}/neighbors", params={"depth": 1})
    assert r.status_code == 200, r.text
    body = r.json()
    for key in ("root", "depth", "nodes", "edges"):
        assert key in body, f"缺少字段 {key}"
    assert body["root"] == LI_BAI
    assert body["depth"] == 1
    assert isinstance(body["nodes"], list)
    # 至少包含 root 自身节点
    assert any(n["id"] == LI_BAI for n in body["nodes"])


def test_entities_list_fields_whitelist(client: TestClient):
    """/api/entities?fields=...：仅返回白名单字段，id/type 强制包含。"""
    r = client.get("/api/entities", params={
        "type": "Person", "limit": 5, "fields": "name,born,died"})
    assert r.status_code == 200, r.text
    items = r.json()["items"]
    assert items, "应返回非空列表"
    for it in items:
        # 白名单 + 强制 id/type，不多不少
        assert set(it.keys()) == {"id", "type", "name", "born", "died"}, it.keys()
        assert it["id"]
        assert it["type"] == "Person"


def test_entities_list_no_fields_unchanged(client: TestClient):
    """未给 fields 时返回全字段（默认合同不变），是 fields 子请求字段的真超集。"""
    r_full = client.get("/api/entities", params={"type": "Person", "limit": 5})
    r_sub = client.get("/api/entities", params={
        "type": "Person", "limit": 5, "fields": "name"})
    assert r_full.status_code == 200 and r_sub.status_code == 200
    full_keys = set(r_full.json()["items"][0].keys())
    sub_keys = set(r_sub.json()["items"][0].keys())
    # 子请求仅 id/type/name
    assert sub_keys == {"id", "type", "name"}
    # 默认响应字段更多（含 bio/sources 等重字段，证明 fields 没有偷偷生效）
    assert sub_keys < full_keys


def test_entities_list_fields_unknown_ignored(client: TestClient):
    """fields 含未知字段名时忽略而非报错，已知字段仍正常返回。"""
    r = client.get("/api/entities", params={
        "type": "Person", "limit": 5, "fields": "name,nonexistent_field_xyz"})
    assert r.status_code == 200, r.text
    for it in r.json()["items"]:
        assert "nonexistent_field_xyz" not in it
        assert {"id", "type", "name"} <= set(it.keys())


def test_entities_filter_role(client: TestClient):
    """/api/entities?type=Person&role=emperor：每项 roles 含 emperor，total 合理。"""
    r = client.get("/api/entities", params={
        "type": "Person", "role": "emperor", "limit": 2000})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["total"] > 0, "emperor 应有样本"
    for it in body["items"]:
        assert "emperor" in (it.get("roles") or []), it["id"]


def test_entities_filter_max_importance(client: TestClient):
    """/api/entities?type=Person&max_importance=2：核心+重要，importance 都 ≤2 且有值。"""
    r = client.get("/api/entities", params={
        "type": "Person", "max_importance": 2, "limit": 2000})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["total"] > 0, "应有核心+重要样本"
    for it in body["items"]:
        imp = it.get("importance")
        assert isinstance(imp, int) and imp <= 2, it["id"]


def test_entities_filter_role_and_importance(client: TestClient):
    """/api/entities?type=Person&role=general&importance=1：组合，每项 roles 含 general 且 importance==1。"""
    r = client.get("/api/entities", params={
        "type": "Person", "role": "general", "importance": 1, "limit": 2000})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["total"] > 0, "核心将领应有样本"
    for it in body["items"]:
        assert "general" in (it.get("roles") or []), it["id"]
        assert it.get("importance") == 1, it["id"]
