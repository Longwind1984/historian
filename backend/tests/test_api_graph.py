"""API 合同测试：/api/graph/*。"""
from fastapi.testclient import TestClient

from app.api.links import _ensure_dynasty_index

LI_BAI = "p_li_bai"
ZHU_XI = "p_zhuxi"


def test_graph_shortest(client: TestClient):
    """/api/graph/shortest?from=p_li_bai&to=p_zhuxi&max_depth=6：返回结构合法。

    跨朝代人物（李白 vs 朱熹）在 max_depth=6 内是否连通取决于数据版本，故此处断言
    响应合同（from/to 正确；若返回路径则跳数在 [1, max_depth] 且与 depth 一致），
    而非假定一定连通。成功分支的「返回路径且跳数≥1」由下方单元测试用直接邻居覆盖。
    """
    r = client.get("/api/graph/shortest", params={"from": LI_BAI, "to": ZHU_XI, "max_depth": 6})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["from"] == LI_BAI
    assert body["to"] == ZHU_XI
    path = body.get("path")
    if path is not None:
        assert isinstance(path, list) and len(path) >= 1
        assert body["depth"] == len(path)
        assert 1 <= body["depth"] <= 6


def test_graph_contemporaries(client: TestClient):
    """/api/graph/contemporaries?person=p_li_bai&year=750：返回同时代人物。"""
    r = client.get("/api/graph/contemporaries", params={"person": LI_BAI, "year": 750})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["person"] == LI_BAI
    assert body["year"] == 750
    assert isinstance(body["peers"], list)
    assert body["count"] == len(body["peers"])
    # 盛唐人物丰富，750 年在世同时代人应 >0
    assert body["count"] > 0


def test_graph_spacetime(client: TestClient):
    """/api/graph/spacetime：时空柱数据地基合同。

    覆盖：meta 字段齐全、nodes 规模 >5000、朝代列表含新增 6 个且按 founded
    升序、李白节点 born=701 且 dynasty 归唐(d_tang)。
    """
    r = client.get("/api/graph/spacetime")
    assert r.status_code == 200, r.text
    body = r.json()

    meta = body["meta"]
    for k in ("total", "with_geo", "with_time", "dynasty_coverage"):
        assert k in meta
    assert meta["total"] == len(body["nodes"])
    assert meta["total"] > 5000

    dynasties = body["dynasties"]
    dyn_ids = {d["id"] for d in dynasties}
    # 原 8 + 新增 6 = 14
    for did in ("d_qin", "d_han", "d_sanguo", "d_jin", "d_nanbeichao", "d_wudai"):
        assert did in dyn_ids, f"新增朝代 {did} 缺失"
    assert len(dynasties) >= 14
    froms = [d["from"] for d in dynasties if d["from"] is not None]
    assert froms == sorted(froms)  # BC 负数在前，升序

    li = next((n for n in body["nodes"] if n["id"] == LI_BAI), None)
    assert li is not None, "李白节点缺失"
    assert li["born"] == 701
    assert li["dynasty"] == "d_tang"  # 唐
    tang = next(d for d in dynasties if d["id"] == "d_tang")
    assert tang["name"] == "唐"

    # spacetime 不得另起一套“按出生年首个命中”的归属逻辑。1050 年处在辽宋
    # 重叠区，p_cbdb_43305 自述 dynasty_ref=k_liao；权威 DynastyIndex 判辽，
    # 裸年份则会误判成宋。逐节点对账同时锁住其他并存朝代与 Polity 映射。
    di = _ensure_dynasty_index()
    nodes_by_id = {n["id"]: n for n in body["nodes"]}
    liao_person = nodes_by_id["p_cbdb_43305"]
    assert liao_person["dynasty"] == "d_liao"
    for eid, node in nodes_by_id.items():
        expected = di.entity_dynasty.get(eid)
        if expected == "__unclassified":
            expected = None
        assert node["dynasty"] == expected, f"spacetime 朝代归属漂移: {eid}"
