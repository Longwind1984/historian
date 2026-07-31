"""API 合同测试：/api/timeline。"""
from fastapi.testclient import TestClient


def test_timeline_range(client: TestClient):
    """/api/timeline?from=600&to=900：返回该时段事件，按年份有序。"""
    r = client.get("/api/timeline", params={"from": 600, "to": 900})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["total"] > 0
    items = body["items"]
    assert isinstance(items, list) and len(items) > 0
    for it in items:
        assert "year" in it and "entity_id" in it and "type" in it
        # 落在查询区间内（None 视为越界，不应出现）
        assert it["year"] is not None
        assert 600 <= it["year"] <= 900
    # 已按 (year, month) 升序
    years = [it["year"] for it in items]
    assert years == sorted(years)
