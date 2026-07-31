"""别名两个键名都要读的回归钉子。

背景:Person/Event 的 schema 声明的是 `alias`(542 个实体),Place 的声明的是
`aliases`(58 个实体 81 条)。搜索的 _rank 曾只读 `alias`,而 _rank 返回 None 即被滤掉 ——
于是那 81 条地点别名对主搜索框不是排得靠后,是彻底搜不到:
搜「建邺」0 条,搜「建康」只回 name 恰为「建康」的那一个。

同仓库 api/links.py:117 早就 `for key in ("alias", "aliases")` 两个都吃,
可见这是键名错配而非有意取舍。

这些钉子防的是:有人"顺手统一"成单个键名,或重构 _rank 时漏掉一个。
"""
import pytest

from app.services.entity_service import list_entities


def _names(q, **kw):
    r = list_entities(q=q, limit=20, **kw)
    return {i["name"] for i in r["items"]}, {i["id"] for i in r["items"]}


def test_place_aliases_key_is_searchable():
    """建康/建业/金陵 同城异名,后两者靠 aliases 才能被「建康」召回。"""
    names, ids = _names("建康", type="Place")
    assert "pl_jianye" in ids, "name 恰为建康的都没召回,搜索坏得更彻底"
    assert len(ids) >= 3, f"只召回 {len(ids)} 条 —— aliases 键又被漏读了:{names}"


def test_alias_only_hit_is_reachable():
    """「建邺」只存在于 pl_jinling 的 aliases 里,name 里没有 —— 纯别名命中。"""
    _, ids = _names("建邺", type="Place")
    assert "pl_jinling" in ids, "纯 aliases 命中不可达,说明只读了 alias 键"


def test_person_alias_key_still_works():
    """别把 Place 修好却把 Person 弄坏 —— 苏东坡只在 p_sushi_song 的 alias 里。"""
    _, ids = _names("苏东坡", type="Person")
    assert "p_sushi_song" in ids, "Person 的 alias 键读不到了"


@pytest.mark.parametrize("q,expect_id", [("建邺", "pl_jinling"), ("苏东坡", "p_sushi_song")])
def test_both_keys_coexist(q, expect_id):
    """两个键名必须同时有效 —— 这正是当初漏掉的那一半。"""
    _, ids = _names(q)
    assert expect_id in ids
