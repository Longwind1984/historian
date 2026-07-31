import pytest
from fastapi.testclient import TestClient


MODERN_EVENT_IDS = (
    "e_aomen_huigui",
    "e_diyike_yuanzidan",
    "e_dongfanghong1",
    "e_sanxia_gongcheng",
    "e_shenzhou5",
    "e_tuopin_gongjian",
    "e_yidai_yilu",
)

PERSON_DYNASTIES = (
    ("p_liu_yilong", "k_liusong"),
    ("p_tuoba_tao", "k_beiwei"),
)

RELATIONS = (
    (
        "p_sun_jiadong",
        "e_dongfanghong1",
        "participated_in",
        "作为‘东方红一号’技术负责人之一，参与中国第一颗人造卫星研制。",
        ["中国科学院·孙家栋与中国探月", "国家航天局·孙家栋：从东方红到嫦娥奔月"],
        None,
    ),
    (
        "p_sun_jiadong",
        "e_change_tanyue",
        "participated_in",
        "任探月工程总设计师，参与嫦娥探月工程。",
        ["中国科学院·孙家栋与中国探月", "国家航天局·孙家栋：从东方红到嫦娥奔月"],
        None,
    ),
    (
        "p_deng_jiaxian",
        "e_diyike_yuanzidan",
        "participated_in",
        "作为中国核武器研制主要组织者之一，参与首颗原子弹研制。",
        [
            "国家国防科技工业局·百年巨匠——邓稼先",
            "中华人民共和国国防部·55年前的惊天一爆，让中国人挺起脊梁",
        ],
        None,
    ),
    (
        "p_yu_min",
        "e_qingdan",
        "participated_in",
        "中国氢弹研制的主要理论奠基者之一，参与首次氢弹试验所涉研制。",
        [
            "中国科学院·于敏个人简介",
            "中国科学院·何祚庥忆于敏：当之无愧的氢弹构型最主要发明者",
        ],
        None,
    ),
    (
        "p_chen_geng",
        "e_kang_mei_yuan_chao",
        "participated_in",
        "抗美援朝期间任中国人民志愿军副司令员。",
        ["大余县人民政府·陈赓", "湖南省纪委监委·陈赓：一门五代皆从戎"],
        None,
    ),
    (
        "p_liu_bocheng",
        "e_chang_zheng",
        "participated_in",
        "长征中任红军总参谋长。",
        [
            "中国军网·政治方向有多重要？习近平从这个故事讲起……",
            "中国军网·长征副刊（2019年2月18日）",
        ],
        None,
    ),
    (
        "p_kang_sheng",
        "e_wen_hua_da_ge_ming",
        "participated_in",
        "文化大革命中任中央文革小组顾问。",
        [
            "人民网·1966年5月28日 中共中央发出关于设立中央文化革命小组的通知",
            "中共中央·关于建国以来党的若干历史问题的决议(1981)",
        ],
        None,
    ),
    (
        "p_xu_xiangqian",
        "e_chang_zheng",
        "participated_in",
        "长征中任红四方面军总指挥，随左路军南下。",
        [
            "中国军网·红四方面军发展历程中的七大里程碑",
            "中国军网·政治方向有多重要？习近平从这个故事讲起……",
        ],
        None,
    ),
    (
        "p_song_qingling",
        "p_sun_zhongshan",
        "spouse_of",
        "孙中山夫人。",
        ["全国政协·宋庆龄（1893—1981）", "中央政府驻港联络办·宋庆龄与保卫中国同盟"],
        None,
    ),
    (
        "p_dai_jitao",
        "p_sun_zhongshan",
        "served_under",
        "民国后任孙中山秘书，长期参与机要。",
        ["中华民国史·戴季陶传", "范小方·戴季陶传"],
        None,
    ),
    (
        "p_tang_shaoyi",
        "p_yuanshikai",
        "served_under",
        "清末长期在朝鲜协助袁世凯；1912年出任内阁总理后因政见不合辞职，关系止于此。",
        ["中华民国史·唐绍仪传", "张维持·唐绍仪传"],
        {"since": {"year": 1885}, "until": {"year": 1912}},
    ),
)


@pytest.mark.parametrize("entity_id", MODERN_EVENT_IDS)
def test_modern_event_is_linked_to_prc(client: TestClient, entity_id: str):
    response = client.get(f"/api/entities/{entity_id}")

    assert response.status_code == 200
    assert "k_prc" in response.json()["polities_involved"]


@pytest.mark.parametrize(("person_id", "dynasty_id"), PERSON_DYNASTIES)
def test_person_has_expected_dynasty(
    client: TestClient, person_id: str, dynasty_id: str
):
    response = client.get(f"/api/entities/{person_id}")

    assert response.status_code == 200
    assert response.json()["dynasty_ref"] == dynasty_id


@pytest.mark.parametrize(
    ("from_id", "to_id", "relation_type", "note", "sources", "boundaries"),
    RELATIONS,
)
def test_high_confidence_relation_is_visible_through_api(
    client: TestClient,
    from_id: str,
    to_id: str,
    relation_type: str,
    note: str,
    sources: list[str],
    boundaries: dict[str, dict[str, int]] | None,
):
    response = client.get(
        "/api/relations",
        params={"from": from_id, "to": to_id, "type": relation_type, "limit": 10},
    )

    assert response.status_code == 200
    matches = [
        item
        for item in response.json()["items"]
        if item["from"] == from_id
        and item["to"] == to_id
        and item["type"] == relation_type
    ]
    assert len(matches) == 1
    assert matches[0]["note"] == note
    assert matches[0]["sources"] == sources
    if boundaries is None:
        assert "since" not in matches[0]
        assert "until" not in matches[0]
    else:
        assert matches[0]["since"] == boundaries["since"]
        assert matches[0]["until"] == boundaries["until"]
