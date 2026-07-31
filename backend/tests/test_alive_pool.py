"""「此刻在世」池子不得先截断后排序的回归钉子。

背景:persons_alive_at 从**生年最晚者**往回扫,凑够 limit+offset 就 break。
entity_service 曾传 limit+offset+200(=230) 取池子,再对已截断的池子做 prefer_seed 排序 ——
于是截断丢的永远是最年长的那批,而年长者恰恰最可能是当年的重量级人物。

实测(修复前):
  1050 年真·在世 372 人,池子只有 230 人,6 个种子被挡在门外 ——
  范仲淹、毕昇、包拯、富弼、欧阳修、韩琦;面板里却排着 13 岁的苏轼。
  1127 年丢掉宗泽、耶律延禧、完颜晟、完颜吴乞买 —— 靖康之变的当事人。

这些钉子防的是:有人为了"省性能"把 limit=None 改回固定窗口。
省下的是 0.07ms(0.13→0.20),换掉的是范仲淹和包拯。
"""
from app.core.data import get_entity_index, load_all_entities
from app.services.entity_service import list_entities


def _truth(year):
    """不走任何快路径,自己算该年在世者 —— 探针必须独立于被测代码。"""
    out = []
    for e in load_all_entities():
        if e.get("type") != "Person":
            continue
        b = (e.get("born") or {}).get("year")
        d = (e.get("died") or {}).get("year")
        if b is None or b > year:
            continue
        if d is not None and d < year:
            continue
        out.append(e)
    return out


def test_senior_seeds_not_dropped_by_pool():
    """1050 年的面板必须有范仲淹和包拯,不能只剩年轻人。"""
    r = list_entities(type="Person", year=1050, limit=16, prefer_seed=True)
    names = [i.get("name") for i in r["items"]]
    for who in ("范仲淹", "包拯", "欧阳修"):
        assert who in names, f"1050 年面板里没有{who} —— 池子又先截断后排序了。实得:{names}"


def test_jingkang_principals_reachable():
    """1127 年靖康之变,宗泽/李纲/赵佶 必须在面板里。"""
    r = list_entities(type="Person", year=1127, limit=16, prefer_seed=True)
    names = [i.get("name") for i in r["items"]]
    for who in ("宗泽", "李纲", "赵佶"):
        assert who in names, f"1127 年面板里没有{who}。实得:{names}"


def test_total_is_true_alive_count():
    """total 曾等于截断后的池子大小(230),而非该年真实在世数(372)。"""
    for y in (1050, 1127, 750):
        r = list_entities(type="Person", year=y, limit=16, prefer_seed=True)
        assert r["total"] == len(_truth(y)), \
            f"{y} 年 total={r['total']},真实在世 {len(_truth(y))} —— total 又坐在截断池子上了"


def test_no_seed_lost_to_window():
    """任何年份,该年在世的种子人物都必须能被取到 —— 不是"排得靠后",是不能消失。"""
    eidx = get_entity_index()
    for y in (1050, 1127, 750, 1600):
        seeds = {e["id"] for e in _truth(y) if not e["id"].startswith("p_cbdb_")}
        got = {p["id"] for p in eidx.persons_alive_at(y, limit=None)}
        lost = seeds - got
        assert not lost, f"{y} 年有 {len(lost)} 个种子取不到:{sorted(lost)[:6]}"
