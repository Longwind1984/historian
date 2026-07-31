"""API 合同测试：/api/relations 分页。"""
from fastapi.testclient import TestClient


def test_relations_pagination_has_stable_metadata(client: TestClient):
    """分页返回 total/offset/limit，连续两页不重叠。"""
    params = {"type": "associated_with", "limit": 10}
    first = client.get("/api/relations", params={**params, "offset": 0})
    second = client.get("/api/relations", params={**params, "offset": 10})
    combined = client.get("/api/relations", params={
        "type": "associated_with", "limit": 20, "offset": 0})
    assert first.status_code == 200, first.text
    assert second.status_code == 200, second.text
    assert combined.status_code == 200, combined.text

    page1 = first.json()
    page2 = second.json()
    assert page1["total"] == page2["total"] > 5000
    assert (page1["offset"], page1["limit"]) == (0, 10)
    assert (page2["offset"], page2["limit"]) == (10, 10)
    assert len(page1["items"]) == len(page2["items"]) == 10

    assert combined.json()["items"] == page1["items"] + page2["items"]


def test_relations_offset_reaches_past_hard_limit(client: TestClient):
    """旧接口 limit 上限为 5000；offset 必须能取到其后的 associated_with。"""
    response = client.get("/api/relations", params={
        "type": "associated_with", "offset": 5000, "limit": 1})
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["total"] > 5000
    assert body["offset"] == 5000
    assert len(body["items"]) == 1


def test_relations_rejects_negative_offset(client: TestClient):
    response = client.get("/api/relations", params={"offset": -1})
    assert response.status_code == 422


def test_high_confidence_event_causal_relation_is_exposed(client: TestClient):
    response = client.get("/api/relations", params={
        "type": "led_to", "from": "e_wang_mang_gaige", "limit": 10})
    assert response.status_code == 200, response.text
    items = response.json()["items"]
    relation = next(r for r in items if r.get("to") == "e_lvlin_chimei")
    assert "王田" in relation["note"]
    assert relation["sources"] == [
        "汉书·王莽传", "后汉书·刘玄传、刘盆子传", "资治通鉴·卷38-41"]
