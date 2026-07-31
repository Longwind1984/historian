"""索引单元测试：EntityIndex（backend/app/core/data.py）。"""
from app.core.data import EntityIndex

LI_BAI = "p_li_bai"
# 劉盈（汉惠帝）：born -205 / died -188，用于 BC 负数年份二分边界测试
LIU_YING = "p_cbdb_16623"


def test_by_id_hit(entity_index: EntityIndex):
    """by_id 命中：p_li_bai -> 李白。"""
    e = entity_index.by_id.get(LI_BAI)
    assert e is not None
    assert e["name"] == "李白"
    assert e["type"] == "Person"
    # get() 等价
    assert entity_index.get(LI_BAI)["name"] == "李白"


def test_by_id_miss(entity_index: EntityIndex):
    """by_id 未命中：不存在的 id 返回 None。"""
    assert entity_index.get("p_does_not_exist_xyz") is None
    assert "p_does_not_exist_xyz" not in entity_index.by_id


def test_by_type_count(entity_index: EntityIndex):
    """by_type 计数：Person 非空，且与 entities_by_type 一致。"""
    by_type = entity_index.by_type
    assert "Person" in by_type
    assert len(by_type["Person"]) > 0
    # entities_by_type 与 by_type 计数一致
    assert len(entity_index.entities_by_type("Person")) == len(by_type["Person"])
    # 未知类型返回空列表
    assert entity_index.entities_by_type("NoSuchType") == []


def test_persons_by_year_basic(entity_index: EntityIndex):
    """persons_alive_at(750) 非空且含李白（born 701 / died 762）。"""
    alive = entity_index.persons_alive_at(750, limit=5000)
    ids = [p["id"] for p in alive]
    assert LI_BAI in ids
    # limit 生效
    assert len(entity_index.persons_alive_at(750, limit=5)) <= 5


def test_persons_by_year_bc_boundary(entity_index: EntityIndex):
    """persons_by_year 二分查找边界：含 BC 负数年份。

    劉盈 born=-205 / died=-188：
      - year=-200：born<=-200 且 died(-188)>=-200 -> 在世
      - year=-205：born<=-205（边界等于 born）-> 在世
      - year=-210：born(-205) > -210 -> 未出生，不在列表
    """
    alive_200 = [p["id"] for p in entity_index.persons_alive_at(-200, limit=5000)]
    assert LIU_YING in alive_200, "劉盈应在 -200 年在世"

    alive_205 = [p["id"] for p in entity_index.persons_alive_at(-205, limit=5000)]
    assert LIU_YING in alive_205, "born 年份边界 -205 应判为在世"

    alive_210 = [p["id"] for p in entity_index.persons_alive_at(-210, limit=5000)]
    assert LIU_YING not in alive_210, "-210 年劉盈尚未出生，不应在世"


def test_persons_by_year_after_death(entity_index: EntityIndex):
    """李白卒于 762，763 年不应在世。"""
    alive_763 = [p["id"] for p in entity_index.persons_alive_at(763, limit=5000)]
    assert LI_BAI not in alive_763
