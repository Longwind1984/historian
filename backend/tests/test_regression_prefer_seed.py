"""回归钉子：prefer_seed=true 行为。

对应历史 bug「此刻在世 0 人」：persons_alive_at 在某些年份返回空。
钉子保证 750 年在世列表非空且含种子人物李白；且 prefer_seed=true 时种子人物
（非 p_cbdb_）排在 CBDB 人物之前。
"""
from fastapi.testclient import TestClient

from app.services.entity_service import list_entities

LI_BAI = "p_li_bai"


def test_alive_at_750_nonempty(entity_index):
    """750 年在世人物非空且含李白（直接打「0 人在世」bug）。"""
    alive = entity_index.persons_alive_at(750, limit=5000)
    assert len(alive) > 0, "750 年在世人物为 0（回归 bug 复现）"
    assert LI_BAI in [p["id"] for p in alive]


def test_prefer_seed_orders_seed_first_service():
    """prefer_seed=true：种子人物排在 CBDB 人物之前（服务层，全量列表）。"""
    # 用大 limit 绕过 API 的 2000 上限，拿到完整在世列表
    res = list_entities(type="Person", year=750, prefer_seed=True, limit=100000)
    items = res["items"]
    assert res["total"] > 0
    ids = [it["id"] for it in items]
    assert LI_BAI in ids, "李白不在 750 在世列表"

    li_bai_idx = ids.index(LI_BAI)
    first_cbdb_idx = next((i for i, x in enumerate(ids) if x.startswith("p_cbdb_")), None)
    # 若存在 CBDB 人物，李白（种子）必须出现在任意 CBDB 之前
    if first_cbdb_idx is not None:
        assert li_bai_idx < first_cbdb_idx, (
            f"prefer_seed 未生效：李白(idx={li_bai_idx}) 排在 CBDB(idx={first_cbdb_idx}) 之后"
        )


def test_prefer_seed_api(client: TestClient):
    """API 层：prefer_seed=true 返回 200，且李白在前 2000 条内。"""
    r = client.get("/api/entities", params={
        "type": "Person", "year": 750, "prefer_seed": True, "limit": 2000,
    })
    assert r.status_code == 200, r.text
    body = r.json()
    ids = [it["id"] for it in body["items"]]
    assert LI_BAI in ids
    first_cbdb_idx = next((i for i, x in enumerate(ids) if x.startswith("p_cbdb_")), None)
    if first_cbdb_idx is not None:
        assert ids.index(LI_BAI) < first_cbdb_idx
