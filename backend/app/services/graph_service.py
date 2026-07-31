"""Graph service: path queries, contemporaries, faction membership."""
from ..core.data import get_relation_index, get_entity_index


def shortest_path(from_id: str, to_id: str, max_depth: int = 4) -> dict:
    ridx = get_relation_index()
    return ridx.shortest_path(from_id, to_id, max_depth)


def contemporaries(person_id: str, year: int, radius: int = 50) -> list[dict]:
    """People alive near the same year as the given person."""
    eidx = get_entity_index()
    target = eidx.get(person_id)
    if not target:
        return []
    born_cutoff = year + radius
    died_cutoff = year - radius
    peers = []
    for p in eidx.entities_by_type("Person"):
        if p.get("id") == person_id:
            continue
        pb = (p.get("born") or {}).get("year")
        pd = (p.get("died") or {}).get("year")
        if pb and pb <= born_cutoff and pd and pd >= died_cutoff:
            peers.append(p)
    return peers


# ---------------------------------------------------------------------------
# Spacetime 数据地基（T3.0）：每实体 时间+地理+朝代+链接度
# ---------------------------------------------------------------------------

# 进程内缓存：按 DATA_DIR 目录签名失效，与 links.py 的 _ensure_* 同步
_spacetime_cache: dict = {"sig": None, "data": None}


def _ym_year(v) -> int | None:
    """year_month 值 -> year 整数（接受 {year,month?} 映射或裸 int；不可解析返 None）。"""
    if isinstance(v, bool):  # bool 是 int 子类，先排除
        return None
    if isinstance(v, int):
        return v
    if isinstance(v, dict):
        y = v.get("year")
        if isinstance(y, bool) or y is None:
            return None
        if isinstance(y, int):
            return y
        try:
            return int(y)
        except (TypeError, ValueError):
            return None
    return None


def _spacetime_years(e: dict) -> tuple[int | None, int | None]:
    """按实体类型提取 (born_year, died_year)，用于朝代归属与时间轴。

    Person: born/died；Event/Battle: date / end_date(缺则同 date)；Polity:
    founded/ended；Faction: founded(无 ended)；Place/Dynasty: 无。
    """
    t = e.get("type")
    if t == "Person":
        return _ym_year(e.get("born")), _ym_year(e.get("died"))
    if t in ("Event", "Battle"):
        b = _ym_year(e.get("date"))
        d = _ym_year(e.get("end_date"))
        return b, (d if d is not None else b)
    if t == "Polity":
        return _ym_year(e.get("founded")), _ym_year(e.get("ended"))
    if t == "Faction":
        return _ym_year(e.get("founded")), None
    return None, None


def _place_xy(pl: dict) -> tuple[float | None, float | None]:
    """Place 实体 -> (x=经度, y=纬度)；无坐标或非数值 -> (None, None)。"""
    lat = pl.get("latitude")
    lng = pl.get("longitude")
    if isinstance(lat, bool) or isinstance(lng, bool):
        return (None, None)
    if isinstance(lat, (int, float)) and isinstance(lng, (int, float)):
        return (float(lng), float(lat))
    return (None, None)


# 实体类型 -> 其地理坐标所引用的 Place ref 字段名
_GEO_REF_FIELD = {
    "Person": "birthplace",
    "Event": "location",
    "Battle": "location",
    "Polity": "capital",
    "Faction": "core_region",
}


def _spacetime_geo(e: dict, by_id: dict) -> tuple[float | None, float | None]:
    """提取 (x=经度, y=纬度)。

    Person->birthplace、Event/Battle->location、Polity->capital、Faction->
    core_region 解引用到 Place 取坐标；Place 取自身 latitude/longitude。
    无 ref / ref 不存在 / Place 无坐标 -> (None, None)（前端排雾环）。
    """
    t = e.get("type")
    if t == "Place":
        return _place_xy(e)
    field = _GEO_REF_FIELD.get(t)
    if not field:
        return (None, None)
    pid = e.get(field)
    if not isinstance(pid, str) or pid not in by_id:
        return (None, None)
    return _place_xy(by_id[pid])


def spacetime() -> dict:
    """时空柱数据地基：每实体 name+type+born+died+x+y+dynasty+links。

    复用点（禁止重扫）：
      - links.py MentionGraph（_ensure_graph）：出/入链度，links = out + in
      - links.py DynastyIndex（_ensure_dynasty_index）：entity_dynasty 权威归属
      - links.py _data_sig()：目录签名，结果按其进程内缓存失效

    朝代归属必须复用 DynastyIndex.entity_dynasty：它优先尊重实体 dynasty_ref 与
    Polity includes，年份只作缺失时回落。spacetime 自行按年份首命中会把辽宋等
    并存朝代重新判错，且与图谱聚合口径分叉。
    """
    # 延迟导入：service 层不在模块加载时反向依赖 api 层，函数内取用即可
    from ..api.links import _ensure_graph, _ensure_dynasty_index, _data_sig, _UNCLASSIFIED

    sig = _data_sig()
    cached = _spacetime_cache["data"]
    if cached is not None and _spacetime_cache["sig"] == sig:
        return cached

    eidx = get_entity_index()
    by_id = eidx.by_id
    graph = _ensure_graph()
    di = _ensure_dynasty_index()

    out_counts = {eid: len(outs) for eid, outs in graph.out_ids.items()}
    in_counts = graph.in_counts_occ

    nodes = []
    with_geo = 0
    with_time = 0
    dyn_count: dict[str, int] = {}

    for e in eidx.entities:
        if e.get("type") == "Dynasty":
            continue  # 朝代本身是时空柱的轴，不进 nodes
        eid = e.get("id")
        if not eid:
            continue
        born, died = _spacetime_years(e)
        x, y = _spacetime_geo(e, by_id)
        did = di.entity_dynasty.get(eid)
        if did == _UNCLASSIFIED:
            did = None
        links = out_counts.get(eid, 0) + in_counts.get(eid, 0)
        nodes.append({
            "id": eid,
            "name": e.get("name"),
            "type": e.get("type"),
            "born": born,
            "died": died,
            "x": x,
            "y": y,
            "dynasty": did,
            "links": links,
        })
        if x is not None:
            with_geo += 1
        if born is not None or died is not None:
            with_time += 1
        if did is not None:
            dyn_count[did] = dyn_count.get(did, 0) + 1

    # 朝代列表：全部 Dynasty 实体，按 founded 升序（BC 负数在前，缺年份在末）
    dynasties = []
    for e in eidx.entities:
        if e.get("type") != "Dynasty":
            continue
        dynasties.append({
            "id": e["id"],
            "name": e.get("name"),
            "from": _ym_year(e.get("founded")),
            "to": _ym_year(e.get("ended")),
        })
    dynasties.sort(key=lambda d: (d["from"] is None, d["from"] if d["from"] is not None else 0))

    # 朝代归属分布：朝代 id -> 节点数，未分类单列（与 links.py __unclassified 一致）
    dynasty_coverage = dict(dyn_count)
    dynasty_coverage["__unclassified"] = max(0, len(nodes) - sum(dyn_count.values()))

    data = {
        "meta": {
            "total": len(nodes),
            "with_geo": with_geo,
            "with_time": with_time,
            "dynasty_coverage": dynasty_coverage,
        },
        "dynasties": dynasties,
        "nodes": nodes,
    }
    _spacetime_cache["sig"] = sig
    _spacetime_cache["data"] = data
    return data
