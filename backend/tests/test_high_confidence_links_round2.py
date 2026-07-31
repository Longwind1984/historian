import pytest
from fastapi.testclient import TestClient


MODERN_EVENTS = (
    "e_beijing_aoyun",
    "e_beijing_dongao",
    "e_shanghai_shibo",
)

DYNASTY_GROUPS = {
    "k_dongwu": ("p_sun_hao", "p_sun_liang", "p_sun_xiu"),
    "k_dongjin": ("p_sima_dan",),
    "k_donghan": (
        "p_liu_bian",
        "p_liu_bing",
        "p_liu_long",
        "p_liu_yi_shaodi",
        "p_liu_zhi_huandi",
        "p_liu_zuan",
    ),
    "k_dong_wei": ("p_yuan_shanjian",),
    "k_yuan": ("p_asugiba", "p_haishan", "p_rinchinbal", "p_shidebala"),
    "k_liusong": ("p_liu_jun", "p_liu_yifu", "p_liu_yu_houfeidi", "p_liu_zhun"),
    "k_bei_zhou": ("p_yuwen_yu", "p_yuwen_yun"),
    "k_beiwei": (
        "p_tuoba_hong_xianwen",
        "p_tuoba_jun",
        "p_yuan_ke",
        "p_yuan_xiu",
        "p_yuan_xu",
        "p_yuan_ye",
        "p_yuan_ziyou",
    ),
    "k_bei_qi": ("p_gao_heng", "p_gao_zhan"),
    "k_nan_qi": ("p_xiao_baojuan", "p_xiao_baorong", "p_xiao_ze", "p_xiao_zhaoye"),
    "k_caowei": ("p_cao_huan",),
    "k_nan_liang": ("p_xiao_dong", "p_xiao_fangzhi", "p_xiao_gang", "p_xiao_yi"),
    "k_xixia": (
        "p_li_bingchang",
        "p_li_chunyou",
        "p_li_dewang",
        "p_li_liangzuo",
        "p_li_qianshun",
        "p_li_renxiao",
        "p_li_xian_xixia",
        "p_li_zunxu",
    ),
    "k_xihan": ("p_liu_gong", "p_liu_hong_shaodi"),
    "k_xi_wei": ("p_yuan_kuo", "p_yuan_qin"),
    "k_liao": ("p_yelv_hongji", "p_yelv_ruan", "p_yelv_yanxi"),
    "k_jin": (
        "p_wanyanwuqimai",
        "p_wanyan_dan",
        "p_wanyan_jing",
        "p_wanyan_xun",
        "p_wanyan_yongji",
    ),
    "k_nan_chen": ("p_chen_bozong", "p_chen_qian"),
}

PERSON_DYNASTIES = tuple(
    (person_id, dynasty_id)
    for dynasty_id, person_ids in DYNASTY_GROUPS.items()
    for person_id in person_ids
)

MARCHES = {
    "e_jian_guo_tang": {
        "from": "pl_taiyuan",
        "to": "pl_daxing",
        "note": (
            "617年李渊自太原起兵，进攻并攻克长安；此段只记晋阳起兵至入长安的"
            "建唐前置军事阶段，不把618年受禅建国概括成行军。《旧唐书·高祖本纪》"
            "《资治通鉴·卷185》"
        ),
        "sources": ["旧唐书·高祖本纪", "资治通鉴·卷185"],
    },
    "e_tang_shoufu_liangjing": {
        "from": "pl_daxing",
        "to": "pl_luoyang_sui",
        "note": (
            "757年九月唐军先收复长安，继而收复洛阳；此段只记收复两京的先后阶段，"
            "不延伸到河北追击。《旧唐书·肃宗本纪》《资治通鉴·卷220》"
        ),
        "sources": ["旧唐书·肃宗本纪", "资治通鉴·卷220"],
    },
    "b_gaolianghe": {
        "from": "pl_taiyuan",
        "to": "pl_youzhou",
        "note": (
            "宋太宗灭北汉后由太原径攻辽南京幽州；此段只记灭北汉后转攻幽州，"
            "不代替高梁河战场内的交战路线。《宋史·太宗本纪》《辽史·景宗本纪》"
        ),
        "sources": ["宋史·太宗本纪", "辽史·景宗本纪"],
    },
    "b_jiahe": {
        "from": "pl_yunzhou_lsd",
        "to": "pl_kaifeng",
        "note": (
            "923年李存勖从郓州突入，直捣汴梁灭后梁；此段只记夹河长期拉锯末期的"
            "郓州至汴梁进军，不概括917—923年全线。《资治通鉴·卷270-272》"
            "《新五代史·唐本纪》"
        ),
        "sources": ["资治通鉴·卷270-272", "新五代史·唐本纪"],
    },
}


@pytest.mark.parametrize("event_id", MODERN_EVENTS)
def test_modern_cultural_event_is_linked_to_prc(client: TestClient, event_id: str):
    response = client.get(f"/api/entities/{event_id}")

    assert response.status_code == 200
    assert response.json()["polities_involved"] == ["k_prc"]


@pytest.mark.parametrize(("person_id", "dynasty_id"), PERSON_DYNASTIES)
def test_orphan_ruler_has_locally_attested_dynasty(
    client: TestClient, person_id: str, dynasty_id: str
):
    response = client.get(f"/api/entities/{person_id}")

    assert response.status_code == 200
    entity = response.json()
    assert entity["dynasty_ref"] == dynasty_id
    assert entity["reign_start"]
    assert entity["reign_end"]
    assert entity["sources"]


def test_julu_battle_uses_battle_place_not_zhang_jiao_birthplace(client: TestClient):
    event_response = client.get("/api/entities/e_julu_zhizhan")
    battle_place_response = client.get("/api/entities/pl_julu_qi")
    birthplace_response = client.get("/api/entities/pl_ju_lu_zhangjiao")

    assert event_response.status_code == 200
    assert battle_place_response.status_code == 200
    assert birthplace_response.status_code == 200
    assert event_response.json()["location"] == "pl_julu_qi"
    assert "BC207 巨鹿之战" in battle_place_response.json()["description"]
    assert "张角籍贯" in birthplace_response.json()["description"]


def test_jin_taizong_has_one_canonical_entity_with_merged_fields(client: TestClient):
    canonical_response = client.get("/api/entities/p_wanyanwuqimai")
    duplicate_response = client.get("/api/entities/p_wanyan_sheng")

    assert canonical_response.status_code == 200
    assert duplicate_response.status_code == 404
    entity = canonical_response.json()
    assert entity["name"] == "完颜吴乞买"
    assert {"完颜晟", "金太宗", "吴乞买"} <= set(entity["alias"])
    assert entity["died"] == {"year": 1135, "month": 2}
    assert entity["reign_start"] == {"year": 1123}
    assert entity["reign_end"] == {"year": 1135}
    assert entity["dynasty_ref"] == "k_jin"
    assert entity["wikidata_id"] == "Q5070"
    assert entity["image_license"] == "CC BY-SA 3.0"


@pytest.mark.parametrize(("entity_id", "expected"), MARCHES.items())
def test_locally_attested_march_is_visible_through_api(
    client: TestClient, entity_id: str, expected: dict
):
    response = client.get(f"/api/entities/{entity_id}")

    assert response.status_code == 200
    entity = response.json()
    assert entity["march"] == [
        {
            "from": expected["from"],
            "to": expected["to"],
            "note": expected["note"],
        }
    ]
    assert entity["sources"] == expected["sources"]
    for source in expected["sources"]:
        assert f"《{source}》" in expected["note"]


def test_youzhou_relief_has_no_march_without_hebei_yizhou(client: TestClient):
    battle_response = client.get("/api/entities/b_youzhou917")
    wrong_place_response = client.get("/api/entities/pl_yizhou")

    assert battle_response.status_code == 200
    assert wrong_place_response.status_code == 200
    assert "march" not in battle_response.json()
    assert wrong_place_response.json()["name"] == "益州"
    assert wrong_place_response.json()["modern_name"] == "成都"
