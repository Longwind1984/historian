"""展开地图历史播放清单的真实性与 API 合同。"""
from fastapi.testclient import TestClient


def test_map_story_is_sorted_and_every_item_has_explicit_geometry(client: TestClient):
    response = client.get("/api/timeline/map-story")
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["total"] == len(body["items"])
    assert body["total"] > 100

    items = body["items"]
    order = [(item["year"], item.get("month") or 0, item.get("day") or 0)
             for item in items]
    assert order == sorted(order)
    for item in items:
        assert item["kind"] in ("event", "life_event")
        assert item["entity_id"] and item["focus_entity_id"]
        assert item["title"] and isinstance(item["year"], int)
        assert item.get("location") or item.get("march")
        if item.get("location"):
            assert item["location"]["latitude"] is not None
            assert item["location"]["longitude"] is not None
        for leg in item.get("march") or []:
            for endpoint in (leg["from"], leg["to"]):
                assert endpoint["latitude"] is not None
                assert endpoint["longitude"] is not None


def test_life_nodes_are_same_year_named_related_events_not_birthplace_guesses(
    client: TestClient, entity_index, relation_index,
):
    items = client.get("/api/timeline/map-story").json()["items"]
    life_items = [item for item in items if item["kind"] == "life_event"]
    assert life_items, "现有本地关系应至少产出一条高置信人物生平节点"

    relation_pairs = {
        frozenset((relation.get("from"), relation.get("to")))
        for relation in relation_index.relations
    }
    for item in life_items:
        person = entity_index.get(item["entity_id"])
        event = entity_index.get(item["focus_entity_id"])
        assert person["type"] == "Person"
        assert person["importance"] in (1, 2)
        assert event["type"] in ("Event", "Battle")
        assert (event.get("date") or {}).get("year") == item["year"]
        assert event["name"] in item["title"]
        assert frozenset((person["id"], event["id"])) in relation_pairs
        assert "birthplace" not in item
        assert item["focus_note"] == f"地点依据同年关联事件「{event['name']}」"

    # 固定一条读者可复核的真数据，防算法收紧后悄悄退化为空清单。
    assert any(item["entity_id"] == "p_zhou_wu_wang"
               and item["focus_entity_id"] == "b_muye"
               for item in life_items)


def test_map_story_range_and_limit(client: TestClient):
    response = client.get("/api/timeline/map-story", params={
        "from": 600, "to": 900, "limit": 3,
    })
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["total"] >= len(body["items"])
    assert len(body["items"]) == 3
    assert all(600 <= item["year"] <= 900 for item in body["items"])
