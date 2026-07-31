"""后汉、后周易代的史料原载农历月回归测试。"""

from fastapi.testclient import TestClient


def _entity(client: TestClient, entity_id: str) -> dict:
    response = client.get(f"/api/entities/{entity_id}")
    assert response.status_code == 200, response.text
    return response.json()


def _relation(
    client: TestClient, relation_type: str, from_id: str, to_id: str
) -> dict:
    response = client.get(
        "/api/relations",
        params={"type": relation_type, "from": from_id, "limit": 100},
    )
    assert response.status_code == 200, response.text
    return next(item for item in response.json()["items"] if item["to"] == to_id)


def test_later_han_zhou_transition_uses_source_lunar_months(client: TestClient):
    """十一月帝卒、十二月监国、次年正月建周，不混入公历换算月。"""
    liu = _entity(client, "p_liuchengyou")
    guo = _entity(client, "p_guowei")
    founding = _entity(client, "e_guo_weizhou")
    later_han = _entity(client, "k_houhan")
    later_zhou = _entity(client, "k_houzhou")

    assert liu["died"] == {"year": 950, "month": 11}
    assert liu["reign_end"] == {"year": 950, "month": 11}
    assert guo["reign_start"] == {"year": 951, "month": 1}
    assert founding["date"] == {"year": 951, "month": 1}
    assert "end_date" not in founding
    assert later_han["ended"] == {"year": 951, "month": 1}
    assert later_zhou["founded"] == {"year": 951, "month": 1}


def test_transition_relations_distinguish_revolt_from_dynastic_change(
    client: TestClient,
):
    """十一月起兵是前因；政权终结、篡位与继承均落在正月即位。"""
    participation = _relation(
        client, "participated_in", "p_liuchengyou", "e_guo_weizhou"
    )
    destroyed = _relation(client, "destroyed_by", "k_houhan", "k_houzhou")
    usurped = _relation(client, "usurped", "p_guowei", "k_houhan")
    succession = _relation(client, "succeeded_by", "k_houhan", "k_houzhou")

    assert participation["since"] == {"year": 950, "month": 11}
    assert destroyed["since"] == {"year": 951, "month": 1}
    assert usurped["since"] == {"year": 951, "month": 1}
    assert succession["since"] == {"year": 951, "month": 1}
