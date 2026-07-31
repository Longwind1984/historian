"""Entity service: filtering, search, year-active queries."""
from ..core.data import (
    load_all_entities, load_entity, load_entities_by_type,
    load_persons_alive, get_entity_index,
)


def _year_active(entity: dict, year: int) -> bool:
    """Check if entity is "active" in a given year."""
    t = entity.get("type")
    if t == "Person":
        born = (entity.get("born") or {}).get("year")
        died = (entity.get("died") or {}).get("year")
        if born and year < born:
            return False
        if died and year > died:
            return False
        return True
    if t == "Polity":
        founded = (entity.get("founded") or {}).get("year")
        ended = (entity.get("ended") or {}).get("year")
        if founded and year < founded:
            return False
        if ended and year > ended:
            return False
        return True
    if t == "Faction":
        founded = (entity.get("founded") or {}).get("year")
        dissolved = (entity.get("dissolved") or {}).get("year")
        if founded and year < founded:
            return False
        if dissolved and year > dissolved:
            return False
        return True
    if t in ("Event", "Battle"):
        date = (entity.get("date") or {}).get("year")
        return date == year
    return True


def _serialize(entity: dict) -> dict:
    return {"id": entity.get("id"), "type": entity.get("type"),
            **{k: v for k, v in entity.items() if k != "type"}}


def _pick_fields(items: list[dict], fields: list[str] | None) -> list[dict]:
    """列表字段白名单过滤：fields 为 None/空时原样返回（保持默认合同不变）；
    给定时仅保留白名单字段并强制包含 id/type，未知字段名天然忽略不报错。"""
    if not fields:
        return items
    allowed = set(fields) | {"id", "type"}
    return [{k: v for k, v in it.items() if k in allowed} for it in items]


def list_entities(
    type: str | None = None,
    year: int | None = None,
    q: str | None = None,
    limit: int = 200,
    offset: int = 0,
    prefer_seed: bool = False,
    fields: list[str] | None = None,
    role: str | None = None,
    importance: int | None = None,
    max_importance: int | None = None,
) -> dict:
    """List entities with optional filters.

    Args:
        prefer_seed: If True, seed entities (non-cbdb) are prioritized in results.
        fields: Optional whitelist of field names; given, each item is trimmed to
            these fields (id/type always included), unknown names ignored.
            None/empty keeps the default full-shape response (list contract).
        role: 若给定，仅返回 roles 数组含该值的人物（字段缺失=不匹配，不报错）。
        importance: 若给定，精确匹配 importance 字段（缺失=不匹配）。
        max_importance: 若给定，importance <= 该值（缺失=不匹配；用于"核心+重要"视图）。
    """
    # 任意身份/重要性过滤都需要逐实体判定，无法走 year 二分快速路径；
    # 故仅当 (Person + year + 无身份过滤) 时保留快速路径，行为对既有合同不变。
    has_role_filter = role is not None or importance is not None or max_importance is not None
    if type and year is not None and type == "Person" and not has_role_filter:
        # 用索引加速
        # 必须取全量再排序：persons_alive_at 从生年最晚者往回扫，先截断就等于按
        # 「谁最年轻」筛人，而 prefer_seed 排序发生在截断之后，救不回没进池子的。
        # 实测（1050 年）：旧的 limit+offset+200=230 窗口把 6 个种子挡在门外 ——
        # 范仲淹、包拯、欧阳修、毕昇、富弼、韩琦，面板里却排着 13 岁的苏轼；
        # 1127 年则丢掉宗泽、耶律延禧、完颜晟 —— 靖康之变的当事人。
        # 代价 0.13ms → 0.20ms（该函数本就 O(N) 重建 born_years，break 省不下量级）。
        results = load_persons_alive(year, limit=None)
        if prefer_seed:
            results.sort(key=lambda p: (
                0 if not p.get("id", "").startswith("p_cbdb_") else 1,
                (p.get("born") or {}).get("year", 0),
            ))
        total = len(results)
        items = _pick_fields(
            [_serialize(e) for e in results[offset:offset + limit]], fields)
        return {"total": total, "offset": offset, "limit": limit, "items": items}

    if type:
        entities = load_entities_by_type(type)
    else:
        entities = load_all_entities()

    if year is not None:
        entities = [e for e in entities if _year_active(e, year)]
    if q:
        ql = q.lower()
        # 命中相关性:此前 name/alias/bio 一视同仁且不排序,结果顺序即文件加载顺序 ——
        # 搜「曹操」头两条是赤壁之战、官渡之战(其 bio 提及曹操),搜「李」全是战役,
        # 本人反而不见。正文提及排最后,精确名在最前。
        def _rank(e):
            name = (e.get("name") or "").lower()
            # 两个键名都要读：Person/Event 的 schema 声明的是 alias（542 个实体），
            # Place 的声明的是 aliases（58 个实体 81 条）。此处曾只读 alias，
            # 而 _rank 返回 None 即被滤掉 —— 所以那 81 条地点别名对主搜索框不是排得靠后，
            # 是彻底搜不到：搜「建邺」0 条，搜「建康」只回 name 恰为建康的那一个。
            # 同仓库 api/links.py:117 早就 for key in ("alias", "aliases") 两个都吃，
            # 可见这是错配而非取舍。
            aliases = [(a or "").lower()
                       for key in ("alias", "aliases")
                       for a in (e.get(key) or [])]
            if name == ql:
                return 0
            if name.startswith(ql):
                return 1
            if ql in name:
                return 2
            if any(a == ql for a in aliases):
                return 3
            if any(ql in a for a in aliases):
                return 4
            # 今名(现代地名)检索:排在 名/别名 之后、正文之前 ——
            # 搜「南京」应召回建业/金陵/天京等 modern_name 含南京的古地名,
            # 但 name/alias 恰含「南京」的实体仍优先。
            modern = (e.get("modern_name") or "").lower()
            if modern:
                if modern == ql:
                    return 5
                if ql in modern:
                    return 6
            if ql in (e.get("bio") or e.get("description") or "").lower():
                return 7
            return None
        scored = [(r, e) for r, e in ((_rank(e), e) for e in entities) if r is not None]
        # 同相关度下种子优先(CBDB 是批量导入,同名时应让位于精编条目)
        scored.sort(key=lambda t: (t[0], 1 if t[1].get("id", "").startswith(("p_cbdb_", "pl_cbdb_")) else 0))
        entities = [e for _, e in scored]
    # 身份/重要性过滤：字段缺失=不匹配（不报错）。仅 Person 有 roles/importance，
    # 非 Person 实体传这些参数会自然得到空集，符合"字段缺失不匹配"约定。
    if role is not None:
        entities = [e for e in entities if role in (e.get("roles") or [])]
    if importance is not None:
        entities = [e for e in entities if e.get("importance") == importance]
    if max_importance is not None:
        entities = [e for e in entities
                    if isinstance(e.get("importance"), int) and e["importance"] <= max_importance]
    # q 分支已按 (相关度, 种子优先) 排过;此处再按种子性排会把相关度打散
    # (稳定排序下,种子的正文命中会压过 CBDB 的精确名命中)。
    if prefer_seed and not q:
        entities.sort(key=lambda p: (
            0 if not p.get("id", "").startswith("p_cbdb_") else 1,
        ))

    total = len(entities)
    items = _pick_fields(
        [_serialize(e) for e in entities[offset:offset + limit]], fields)
    return {
        "total": total,
        "offset": offset,
        "limit": limit,
        "items": items,
    }


def get_entity(entity_id: str) -> dict | None:
    e = load_entity(entity_id)
    if e is None:
        return None
    return _serialize(e)


def get_neighbors(entity_id: str, depth: int = 1) -> dict:
    """Get related entities via BFS."""
    from ..core.data import get_relation_index
    eidx = get_entity_index()
    ridx = get_relation_index()

    visited_ids, found_relations = ridx.neighbors(entity_id, depth)

    nodes = [
        {k: v for k, v in e.items()
         if k in ("id", "type", "name", "image", "born", "died",
                   "founded", "ended", "color", "gender", "courtesy_name",
                   "art_name", "modern_name")}
        for eid, e in eidx.by_id.items()
        if eid in visited_ids
    ]
    if not any(n["id"] == entity_id for n in nodes):
        nodes.append({"id": entity_id, "type": "Unknown", "name": entity_id})

    return {
        "root": entity_id,
        "depth": depth,
        "nodes": nodes,
        "edges": [
            {"from": r.get("from"), "to": r.get("to"), "type": r.get("type"),
             "since": r.get("since"), "until": r.get("until"), "note": r.get("note")}
            for r in found_relations
        ],
    }
