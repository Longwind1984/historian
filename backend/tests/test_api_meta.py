"""API 合同测试：/api/meta/*。"""
from fastapi.testclient import TestClient


def test_meta_stats(client: TestClient):
    """/api/meta/stats：实体总数 >7000，按类型计数字段齐全。"""
    r = client.get("/api/meta/stats")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["entity_count"] > 7000, f"entity_count={body['entity_count']}"
    assert body["relation_count"] > 0
    by_type = body["entities_by_type"]
    assert isinstance(by_type, dict) and len(by_type) >= 6
    # 有数据的类型计数都应为正
    for t in ("Person", "Polity", "Event", "Battle"):
        assert t in by_type, f"缺少类型 {t}"
        assert by_type[t] > 0, f"{t} 计数为 0"


def test_meta_schema(client: TestClient):
    """/api/meta/schema：包含 Person/Polity/Event/Battle/Faction/Place/Title 类型。"""
    r = client.get("/api/meta/schema")
    assert r.status_code == 200, r.text
    body = r.json()
    node_types = body["node_types"]
    assert isinstance(node_types, dict)
    for t in ("Person", "Polity", "Event", "Battle", "Faction", "Place", "Title"):
        assert t in node_types, f"schema 缺少节点类型 {t}"
        assert "type" in node_types[t]
