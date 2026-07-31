"""朝代归属的回归钉子。

背景:朝代区间彼此重叠(辽 916~1125 与宋 960~1279 本就并存),而归属曾是「按 founded
升序取首个命中」——辽 founded 916 早于宋 960,于是 960~1125 出生的人全被判成辽人:
「辽」拿到 748 人,是最大的一档,超过唐(553)和宋(427),而库中真辽人只有 32 个。

根子:1050 年的人是辽是宋,取决于他在哪,不取决于他在何时。年份判不了。
现按 dynasty_ref(人物所属政权)→ includes 关系 → 朝代 查表,年份仅作回落。

这些钉子专防那次退化:改 ranges 排序、动 includes、或让 dynasty_ref 失效,都会踩响。
"""
import collections

from app.api.links import _ensure_dynasty_index, _COEXISTING_DYNASTIES
from app.core.data import load_all_entities


def _counts():
    di = _ensure_dynasty_index()
    ents = {e["id"]: e for e in load_all_entities()}
    c = collections.Counter()
    for eid, did in di.entity_dynasty.items():
        e = ents.get(eid)
        if not e or e.get("type") != "Person":
            continue
        c[ents[did]["name"] if did in ents else None] += 1
    return c, di, ents


def test_liao_not_swallowing_song():
    """辽只该拿到真辽人。曾因区间重叠 + 先到先得而拿到 748 人。"""
    c, _, _ = _counts()
    assert c["辽"] < 100, f"辽 分到 {c['辽']} 人 —— 它又把并存的宋人吞了"
    assert c["宋"] > c["辽"] * 10, f"宋 {c['宋']} vs 辽 {c['辽']}:宋人远多于辽人才对"


def test_dynasty_ref_is_authoritative():
    """带 dynasty_ref 的人物,归属必须与其政权所属断代一致,不受年份区间摆布。"""
    _, di, ents = _counts()
    checked = mismatch = 0
    for e in ents.values():
        if e.get("type") != "Person":
            continue
        ref = e.get("dynasty_ref")
        if not isinstance(ref, str):
            continue
        expect = di.polity_dynasty.get(ref)
        if expect is None:
            continue
        checked += 1
        if di.entity_dynasty.get(e["id"]) != expect:
            mismatch += 1
    assert checked > 4000, f"只核到 {checked} 人,dynasty_ref 或 includes 可能失效了"
    assert mismatch == 0, f"{mismatch} 人的归属与其 dynasty_ref 不符"


def test_every_polity_maps_to_a_dynasty():
    """includes 必须覆盖全部 Polity —— 漏一个,那个政权的人就只能靠年份猜。"""
    _, di, ents = _counts()
    pol = {i for i, e in ents.items() if e.get("type") == "Polity"}
    missing = pol - set(di.polity_dynasty)
    assert not missing, f"这些 Polity 没归入任何断代:{sorted(missing)}"


def test_coexisting_dynasties_sorted_last():
    """并存朝代必须排在年份回落匹配的末尾,否则又会独吞重叠年份。"""
    di = _ensure_dynasty_index()
    ids = [r[0] for r in di.ranges]
    coex_pos = [i for i, d in enumerate(ids) if d in _COEXISTING_DYNASTIES]
    assert coex_pos, "并存朝代不在 ranges 里?"
    assert min(coex_pos) > len(ids) - len(coex_pos) - 1, \
        f"并存朝代未排到末尾:{[ids[i] for i in coex_pos]} 位置 {coex_pos}/{len(ids)}"
