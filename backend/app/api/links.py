"""
Wiki-style links (Obsidian Graph view feature).

In Obsidian, putting `[[note title]]` in a note's body creates an outbound
link, and the target note shows a backlink automatically. We do the same:

  - For each entity's `bio` / `description` / `significance` / `impact` /
    `note` text, scan for occurrences of any other entity's name.
  - `/api/links/scan/{id}` returns outbound mentions (entity_id -> mentions).
  - `/api/links/backlinks/{id}` returns inbound mentions (who mentions this entity).

性能策略（T2.3）：
  - NameIndex（名字 -> id）与 MentionGraph（全量出/入链）都是进程内单例，
    首次请求时构建一次，后续热请求直接查表。
  - 失效复用 data.py 的目录签名（_dir_signature：最新 mtime + 文件数），
    DATA_DIR 文件变化后自动重建。签名带短 TTL 缓存，避免每次热请求都 stat
    7000+ 文件。
  - 一次 _scan_dual 同时产出两种命中：占位贪心（出链，长名优先不重叠）与
    全量命中（入链，等价原 regex 子串语义），保证 /scan 与 /backlinks 输出
    与改造前逐条一致。
"""
from __future__ import annotations
import threading
import time
from fastapi import APIRouter, Query, HTTPException

from ..core.data import (
    load_all_entities,
    load_all_relations,
    reload_all,
    _dir_signature,
    settings,
)

# 与中原断代并存、非其继承的朝代。年份回落匹配时排到末尾再试：它们的区间与中原断代
# 大幅重叠（辽 916~1125 之于宋 960~1279），而匹配是「首个命中即返回」，辽 founded 916
# 早于宋 960，不排后面就会把 960~1125 出生的人全判成辽人。
# 这不是「谁是正统」的判断，是修一个「先到先得」的实现细节：库中真正的辽人（32 个）
# 都带 dynasty_ref，走不到这条回落路径。
_COEXISTING_DYNASTIES = {"d_liao", "d_jin_jurchen"}


def _build_polity_dynasty(index) -> dict[str, str]:
    """Polity id -> Dynasty id，来自 includes 关系（Dynasty → Polity）。

    此前该关系只填了 9 个朝代 14 条，Polity → Dynasty 无表可查，归属只能靠年份猜。
    现已填全（data/relations/dynasty_includes.yaml，84 条覆盖全部 Polity）。
    """
    out: dict[str, str] = {}
    for r in load_all_relations():
        if not isinstance(r, dict) or r.get("type") != "includes":
            continue
        src, dst = r.get("from"), r.get("to")
        if not isinstance(src, str) or not isinstance(dst, str):
            continue
        s = index._entities_by_id.get(src)
        d = index._entities_by_id.get(dst)
        if s and d and s.get("type") == "Dynasty" and d.get("type") == "Polity":
            out[dst] = src
    return out

router = APIRouter()


# ---------------------------------------------------------------------------
# 签名：复用 data.py 的目录签名策略，带短 TTL 缓存
# ---------------------------------------------------------------------------

# 热请求每次都要验签名，但 _dir_signature 要 stat 遍历 7000+ YAML（~数十 ms）。
# 缓存签名 TTL 秒：TTL 内直接复用，过期才重算。数据变化最长 TTL 秒后感知。
_SIG_TTL = float(2.0)
_sig_cache: dict = {"sig": None, "ts": 0.0}

# FastAPI 会把同步端点放进线程池。实体档案的链接页会并发请求 scan/backlinks/count；
# 若图尚未冷建，三个线程不能同时对同一个全局单例 build（既重复 O(N×names) 工作，
# 又在 build 过程中暴露半成品字典）。RLock 也覆盖 NameIndex 的失效重建；之所以用
# 可重入锁，是因为 _ensure_graph() 在锁内会调用 _ensure_index()。
_BUILD_LOCK = threading.RLock()


def _data_sig():
    """DATA_DIR 目录签名，带 TTL 缓存。"""
    now = time.monotonic()
    sig = _sig_cache["sig"]
    if sig is not None and now - _sig_cache["ts"] < _SIG_TTL:
        return sig
    sig = _dir_signature(settings.data_dir)
    _sig_cache["sig"] = sig
    _sig_cache["ts"] = now
    return sig


# ---------------------------------------------------------------------------
# Name index
# ---------------------------------------------------------------------------

class NameIndex:
    """Map entity name (or alias) -> entity id. Longest-name-first matching."""

    def __init__(self):
        self._name_to_ids: dict[str, set[str]] = {}  # name -> set(eid)
        self._all_names: list[tuple[str, str]] = []  # (name, id) sorted by len desc
        # 字符 trie；空字符串键保存 [(原 names 排名, name, eid)]。
        # 排名用于在扫描后恢复旧算法“名字长度降序、同长沿 _all_names 顺序”的优先级。
        self._name_trie: dict = {}
        self._entities_by_id: dict[str, dict] = {}
        self._built = False
        self._sig = None  # 构建时对应的 DATA_DIR 签名

    def build(self, entities: list[dict] | None = None):
        if entities is None:
            entities = load_all_entities()
        self._name_to_ids = {}
        self._all_names = []
        self._entities_by_id = {e["id"]: e for e in entities if e.get("id")}

        for e in entities:
            if not e.get("id"):
                continue
            eid = e["id"]
            names_for_entity = set()
            # primary name
            n = e.get("name")
            if n and isinstance(n, str) and len(n) >= 2:
                names_for_entity.add(n)
            # aliases
            for key in ("alias", "aliases"):
                vals = e.get(key) or []
                if isinstance(vals, list):
                    for v in vals:
                        if isinstance(v, str) and len(v) >= 2:
                            names_for_entity.add(v)
            # courtesy / art name
            for key in ("courtesy_name", "art_name"):
                v = e.get(key)
                if isinstance(v, str) and len(v) >= 2:
                    names_for_entity.add(v)
            # modern_name for places
            v = e.get("modern_name")
            if isinstance(v, str) and len(v) >= 2:
                names_for_entity.add(v)

            for nm in names_for_entity:
                self._name_to_ids.setdefault(nm, set()).add(eid)
                self._all_names.append((nm, eid))

        # Sort by length desc so longest match wins during scanning
        self._all_names.sort(key=lambda x: -len(x[0]))
        trie: dict = {}
        for rank, (name, eid) in enumerate(self._all_names):
            node = trie
            for char in name:
                node = node.setdefault(char, {})
            node.setdefault("", []).append((rank, name, eid))
        self._name_trie = trie
        self._built = True

    @property
    def names(self) -> list[tuple[str, str]]:
        if not self._built:
            self.build()
        return self._all_names

    def ids_for_name(self, name: str) -> set[str]:
        if not self._built:
            self.build()
        return self._name_to_ids.get(name, set())

    @property
    def trie(self) -> dict:
        if not self._built:
            self.build()
        return self._name_trie

    def entity(self, eid: str) -> dict | None:
        if not self._built:
            self.build()
        return self._entities_by_id.get(eid)


_INDEX = NameIndex()


def _ensure_index():
    """确保名字索引已构建且与当前 DATA_DIR 签名一致；不一致则重建。

    原实现 _built 一旦 True 永不重建，数据改动后索引陈旧。这里挂到目录签名：
    签名变化时先 reload_all()（重读磁盘实体/关系，绕过 EntityIndex 单例缓存），
    再重建 NameIndex。
    """
    with _BUILD_LOCK:
        sig = _data_sig()
        if not _INDEX._built or _INDEX._sig != sig:
            if _INDEX._built:
                reload_all()
            _INDEX.build()
            _INDEX._sig = sig
        return sig


# ---------------------------------------------------------------------------
# Text scanning
# ---------------------------------------------------------------------------

# We extract the union of free-text fields per entity.
TEXT_FIELDS = ("bio", "description", "significance", "impact", "note", "pres_loc")


def _scan_dual(text: str):
    """一次扫描产出两种命中（需先 _ensure_index）。

    返回 (occupied_hits, all_hits)：
      - occupied_hits: 占位贪心（长名优先、不重叠），按 offset 升序。
        供出链 /scan、/global，与原 _scan_for_mentions 逐条等价。
      - all_hits: 全部命中（含重叠、不去重），等价于「任一名字子串出现」。
        供入链 /backlinks，与原 regex search 语义一致。
    """
    if not text:
        return [], []
    occupied = [False] * len(text)
    occupied_hits: list[dict] = []

    # 旧算法对每段文字逐个执行约 8800 个 str.find，即便绝大多数名字根本不在文中，
    # 全库仍产生 6700 万次 find。trie 改为沿正文字符前缀查找，只访问可能命中的路径。
    # ranked_hits 之后按原 _all_names 排名稳定排序，故“长名先占位”、同长优先级不变。
    ranked_hits: list[tuple[int, int, str, str]] = []  # (rank, offset, eid, name)
    last_end_by_rank: dict[int, int] = {}
    trie = _INDEX.trie
    text_len = len(text)
    for idx in range(text_len):
        node = trie
        cursor = idx
        while cursor < text_len:
            node = node.get(text[cursor])
            if node is None:
                break
            cursor += 1
            for rank, name, eid in node.get("", ()):
                # 原循环命中后令 start=end，因此同一名字的自重叠命中会被跳过。
                if idx < last_end_by_rank.get(rank, -1):
                    continue
                ranked_hits.append((rank, idx, eid, name))
                last_end_by_rank[rank] = cursor

    ranked_hits.sort(key=lambda hit: hit[0])  # stable：同一 rank 保留正文 offset 升序
    all_hits: list[tuple[int, str, str]] = [
        (idx, eid, name) for _rank, idx, eid, name in ranked_hits
    ]

    # names 已按长度降序：长名先占有其出现位置，短名只能在剩余空隙匹配。
    for _rank, idx, eid, name in ranked_hits:
        end = idx + len(name)
        if not any(occupied[idx:end]):
            for i in range(idx, end):
                occupied[i] = True
            occupied_hits.append({
                "id": eid,
                "name": name,
                "offset": idx,
                "length": len(name),
            })
    occupied_hits.sort(key=lambda m: m["offset"])
    return occupied_hits, all_hits


# ---------------------------------------------------------------------------
# Mention graph (cached)
# ---------------------------------------------------------------------------

class MentionGraph:
    """全量 mention 图：出链（占位语义）+ 入链（regex 语义），进程内缓存。

    字段：
      - out_detail[eid]: 去重后的出向 mention 详情（/scan 用，含 field/offset）
      - out_ids[eid]:    去重后的 to_id 列表（/global、/count 用）
      - in_detail[eid]:  反向入链详情（/backlinks 用，from_*/field）
      - in_counts_occ[eid]: 占位语义反向计数（/global 的 "in" 用；与 /backlinks
        的 regex 语义不同，保留两套以与原实现逐端点一致）
    """

    def __init__(self):
        self.out_detail: dict[str, list[dict]] = {}
        self.out_ids: dict[str, list[str]] = {}
        self.in_detail: dict[str, list[dict]] = {}
        self.in_counts_occ: dict[str, int] = {}
        self._built = False
        self._sig = None

    def build(self, index: NameIndex):
        self.out_detail = {}
        self.out_ids = {}
        self.in_detail = {}
        self.in_counts_occ = {}

        for src in index._entities_by_id.values():
            sid = src["id"]
            out_mentions: list[dict] = []
            field_first: dict[str, str] = {}  # to_id -> 首次命中的 field（按 TEXT_FIELDS 顺序）
            for field in TEXT_FIELDS:
                v = src.get(field)
                if not isinstance(v, str) or not v:
                    continue
                occ, all_hits = _scan_dual(v)
                for m in occ:
                    if m["id"] == sid:
                        continue  # 不自链
                    tgt = index.entity(m["id"])
                    out_mentions.append({
                        "to_id": m["id"],
                        "to_name": m["name"],
                        "to_type": tgt.get("type") if tgt else None,
                        "field": field,
                        "offset": m["offset"],
                        "length": m["length"],
                    })
                for (_idx, eid, _name) in all_hits:
                    if eid == sid:
                        continue
                    if eid not in field_first:
                        field_first[eid] = field
            # 跨字段去重 by to_id，保留首次出现
            seen = set()
            dedup: list[dict] = []
            for m in out_mentions:
                if m["to_id"] not in seen:
                    seen.add(m["to_id"])
                    dedup.append(m)
            self.out_detail[sid] = dedup
            self.out_ids[sid] = [m["to_id"] for m in dedup]
            for to_id, field in field_first.items():
                self.in_detail.setdefault(to_id, []).append({
                    "from_id": sid,
                    "from_name": src.get("name"),
                    "from_type": src.get("type"),
                    "field": field,
                })

        # 占位语义反向计数（/global 的 in 用）
        for sid, outs in self.out_ids.items():
            for to in outs:
                self.in_counts_occ[to] = self.in_counts_occ.get(to, 0) + 1

        self._built = True


_GRAPH = MentionGraph()


def _ensure_graph():
    """确保 mention 图已构建且与当前签名一致。"""
    with _BUILD_LOCK:
        sig = _ensure_index()
        # 等锁的并发请求必须在锁内重新检查：第一个线程可能已经完成冷建。
        if not _GRAPH._built or _GRAPH._sig != sig:
            t0 = time.perf_counter()
            _GRAPH.build(_INDEX)
            _GRAPH._sig = sig
            dt = time.perf_counter() - t0
            print(
                f"[links] mention graph built in {dt:.2f}s "
                f"(entities={len(_INDEX._entities_by_id)})",
                flush=True,
            )
        return _GRAPH


# ---------------------------------------------------------------------------
# Dynasty 归属索引（朝代聚合视图 T2.2 用）
# ---------------------------------------------------------------------------

_UNCLASSIFIED = "__unclassified"


class DynastyIndex:
    """entity -> dynasty 归属索引（朝代聚合视图用），进程内缓存。

    归属规则：取实体 born.year（缺失则 died.year），落在某朝代
    [founded.year, ended.year] 区间则归该朝代；无年份或不在任何区间 ->
    __unclassified。仅 8 个 Dynasty 实体，线性匹配 O(N) 足够。
    """

    def __init__(self):
        self.ranges: list[tuple[str, str, int, int]] = []
        # (dynasty_id, name, founded_year, ended_year)，按 founded 升序
        self.entity_dynasty: dict[str, str] = {}  # entity_id -> dynasty_id
        self._built = False
        self._sig = None

    def build(self, index: NameIndex):
        ranges = []
        for e in index._entities_by_id.values():
            if e.get("type") != "Dynasty":
                continue
            f = e.get("founded")
            ed = e.get("ended")
            fy = f.get("year") if isinstance(f, dict) else None
            ey = ed.get("year") if isinstance(ed, dict) else None
            if fy is None or ey is None:
                continue  # 区间不全，跳过该朝代
            ranges.append((e["id"], e.get("name") or e["id"], fy, ey))
        # 并存朝代排到末尾：见 _COEXISTING_DYNASTIES 的说明。
        ranges.sort(key=lambda r: (r[0] in _COEXISTING_DYNASTIES, r[2]))
        self.ranges = ranges

        # Polity -> Dynasty 查表，来自 includes 关系（data/relations/dynasty_includes.yaml，
        # 84 条，覆盖全部 Polity）。这是归属的第一依据：年份判不了 1050 年的人是辽是宋，
        # 那取决于他在哪。
        self.polity_dynasty = _build_polity_dynasty(index)

        ed_map = {}
        for e in index._entities_by_id.values():
            eid = e["id"]
            if e.get("type") == "Dynasty":
                ed_map[eid] = _UNCLASSIFIED  # 朝代实体自身不参与人物归属
                continue
            # 一等依据：实体自述的政权（dynasty_ref -> Polity -> Dynasty）。
            # 4804 个人物带此字段；缺了才回落到年份。
            ref = e.get("dynasty_ref")
            if isinstance(ref, str):
                did = self.polity_dynasty.get(ref)
                if did is not None:
                    ed_map[eid] = did
                    continue
            # Polity 自身归入其所属断代
            if e.get("type") == "Polity":
                did = self.polity_dynasty.get(eid)
                if did is not None:
                    ed_map[eid] = did
                    continue
            yr = None
            b = e.get("born")
            if isinstance(b, dict) and b.get("year") is not None:
                yr = b.get("year")
            else:
                d = e.get("died")
                if isinstance(d, dict) and d.get("year") is not None:
                    yr = d.get("year")
            if yr is None:
                ed_map[eid] = _UNCLASSIFIED
                continue
            # 二等依据：年份落区间。ranges 按 founded 升序、首个命中即返回，而朝代区间
            # 彼此重叠（辽 916~1125 与宋 960~1279 本就并存），故此法对并存期不可靠——
            # 仅用于无 dynasty_ref 者。并存朝代（辽/金/西夏之属）排到末尾再试，
            # 使重叠年份优先落到与之并存的中原断代，而非因 founded 早而独吞。
            assigned = _UNCLASSIFIED
            for did, _name, fy, ey in ranges:
                if fy <= yr <= ey:
                    assigned = did
                    break
            ed_map[eid] = assigned
        self.entity_dynasty = ed_map
        self._built = True


_DYNASTY_INDEX = DynastyIndex()


def _ensure_dynasty_index():
    """确保朝代归属索引已构建且与当前签名一致。复用 _ensure_index 的签名。"""
    sig = _ensure_index()
    if not _DYNASTY_INDEX._built or _DYNASTY_INDEX._sig != sig:
        _DYNASTY_INDEX.build(_INDEX)
        _DYNASTY_INDEX._sig = sig
    return _DYNASTY_INDEX


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.get("/scan/{entity_id}")
def outbound_links(entity_id: str):
    """Return outbound wiki-mentions found in this entity's text fields.

    Returns: { entity_id, mentions: [{ to_id, to_name, field, offset }] }
    """
    _ensure_graph()
    if not _INDEX.entity(entity_id):
        raise HTTPException(404, f"Entity {entity_id} not found")
    mentions = _GRAPH.out_detail.get(entity_id, [])
    return {"entity_id": entity_id, "count": len(mentions), "mentions": mentions}


@router.get("/backlinks/{entity_id}")
def backlinks(entity_id: str):
    """Return entities whose text mentions this entity's name/aliases.

    Returns: { entity_id, count, backlinks: [{ from_id, from_name, from_type, field }] }
    """
    _ensure_graph()
    if not _INDEX.entity(entity_id):
        raise HTTPException(404, f"Entity {entity_id} not found")
    backlinks_list = _GRAPH.in_detail.get(entity_id, [])
    return {"entity_id": entity_id, "count": len(backlinks_list), "backlinks": backlinks_list}


@router.get("/count/{entity_id}")
def link_counts(entity_id: str):
    """Return both outbound and inbound counts (cheap)."""
    _ensure_graph()
    if not _INDEX.entity(entity_id):
        raise HTTPException(404, f"Entity {entity_id} not found")
    return {
        "entity_id": entity_id,
        "outbound": len(_GRAPH.out_ids.get(entity_id, [])),
        "inbound": len(_GRAPH.in_detail.get(entity_id, [])),
    }


@router.post("/rebuild")
def rebuild_index():
    """Force-rebuild the name index + mention graph (call after data changes)."""
    # 强制重读磁盘（绕过 EntityIndex 单例缓存），并刷新签名缓存使后续 _ensure_* 不误判
    reload_all()
    sig = _dir_signature(settings.data_dir)
    _sig_cache["sig"] = sig
    _sig_cache["ts"] = time.monotonic()
    _INDEX.build()
    _INDEX._sig = sig
    _GRAPH._built = False
    _ensure_graph()
    return {"ok": True, "name_count": len(_INDEX._all_names)}


@router.get("/search")
def text_search(q: str = Query(..., min_length=1), limit: int = Query(20, ge=1, le=100)):
    """Full-text search across all entity text fields. Returns ranked hits.

    独立于 mention 图：按名字/别名/正文字段打分，不涉及名字匹配扫描，
    故不走 MentionGraph 缓存。数据变化经 _ensure_index 签名失效自动感知。
    """
    _ensure_index()
    ql = q.lower()
    hits = []
    for e in _INDEX._entities_by_id.values():
        score = 0
        # name exact (highest)
        if e.get("name") and e["name"] == q:
            score += 100
        elif e.get("name") and ql in e["name"].lower():
            score += 50
        # alias
        for k in ("alias", "aliases"):
            for v in (e.get(k) or []):
                if isinstance(v, str) and v == q:
                    score += 80
                elif isinstance(v, str) and ql in v.lower():
                    score += 30
        # text fields
        for field in TEXT_FIELDS:
            v = e.get(field)
            if isinstance(v, str) and ql in v.lower():
                score += 5
        if score > 0:
            hits.append({
                "id": e["id"],
                "name": e.get("name"),
                "type": e.get("type"),
                "score": score,
                "image": e.get("image"),
            })
    hits.sort(key=lambda x: -x["score"])
    return {"q": q, "count": len(hits[:limit]), "hits": hits[:limit]}


# ---------------------------------------------------------------------------
# Global graph overview (Obsidian-style global Graph view)
# ---------------------------------------------------------------------------

@router.get("/global")
def global_graph(
    limit: int = Query(150, ge=10, le=400, description="Max nodes to return"),
    min_links: int = Query(1, ge=0, description="Min outbound+inbound link count"),
):
    """Return a sample of the global wiki-link graph.

    Strategy:
      - Compute link counts for every entity.
      - Keep the top `limit` entities by (outbound + inbound) link count.
      - Compute edges between kept entities only (induced subgraph).
      - This gives a "spine" view: the most-connected entities in the corpus.
    """
    graph = _ensure_graph()
    # 计数全部从预建图取，不再每次全量扫描
    out_counts = {eid: len(outs) for eid, outs in graph.out_ids.items()}
    in_counts = graph.in_counts_occ  # 占位语义反向

    # Score = out + in. Filter min_links.
    scored = []
    for eid in _INDEX._entities_by_id:
        s = out_counts.get(eid, 0) + in_counts.get(eid, 0)
        if s >= min_links:
            scored.append((s, eid))
    scored.sort(key=lambda x: -x[0])
    top_ids = set(eid for _, eid in scored[:limit])

    nodes = []
    edges = []
    edge_seen = set()
    for eid in top_ids:
        e = _INDEX.entity(eid)
        if not e:
            continue
        nodes.append({
            "id": eid,
            "name": e.get("name"),
            "type": e.get("type"),
            "image": e.get("image"),
            "born": e.get("born"),
            "died": e.get("died"),
            "out": out_counts.get(eid, 0),
            "in": in_counts.get(eid, 0),
        })
        for to in graph.out_ids.get(eid, []):
            if to in top_ids:
                key = (eid, to)
                if key in edge_seen:
                    continue
                edge_seen.add(key)
                edges.append({"from": eid, "to": to, "type": "wiki_link"})
    return {
        "node_count": len(nodes),
        "edge_count": len(edges),
        "truncated": len(scored) > limit,
        "total_eligible": len(scored),
        "nodes": nodes,
        "edges": edges,
    }


# ---------------------------------------------------------------------------
# Global graph by dynasty (T2.2 渐进式全局视图)
# ---------------------------------------------------------------------------

@router.get("/global_by_dynasty")
def global_by_dynasty():
    """朝代聚合全局视图（level 1）：每个朝代一个节点，跨朝代双链为边。

    复用 _ensure_graph() 的 mention 图与 _ensure_dynasty_index() 的归属索引，
    不重新全量扫描文本。仅统计有出/入链的实体（双链实体）。
    """
    graph = _ensure_graph()
    di = _ensure_dynasty_index()
    ed_map = di.entity_dynasty

    out_counts = {eid: len(outs) for eid, outs in graph.out_ids.items()}
    in_counts = graph.in_counts_occ

    # 双链实体：out+in >= 1
    linked_ids = set()
    for eid in _INDEX._entities_by_id:
        if out_counts.get(eid, 0) + in_counts.get(eid, 0) >= 1:
            linked_ids.add(eid)

    # 朝代节点统计
    dyn_entity_count: dict[str, int] = {}
    dyn_link_count: dict[str, int] = {}
    for eid in linked_ids:
        did = ed_map.get(eid, _UNCLASSIFIED)
        dyn_entity_count[did] = dyn_entity_count.get(did, 0) + 1
        dyn_link_count[did] = dyn_link_count.get(did, 0) + out_counts.get(eid, 0)

    # 朝代名：真实朝代取实体 name，未分类固定「未分类」
    dyn_name = {did: name for (did, name, _fy, _ey) in di.ranges}
    dyn_name[_UNCLASSIFIED] = "未分类"

    # 仅含有链实体的朝代出现；排序：未分类最后，其余按 founded 升序
    founded_order = {did: fy for (did, _n, fy, _ey) in di.ranges}
    dynasties = [
        {
            "id": did,
            "name": dyn_name.get(did, did),
            "entity_count": dyn_entity_count.get(did, 0),
            "link_count": dyn_link_count.get(did, 0),
        }
        for did in dyn_entity_count
    ]
    dynasties.sort(key=lambda d: (d["id"] == _UNCLASSIFIED, founded_order.get(d["id"], 9999), d["id"]))

    # 跨朝代无向边：(min, max) 字典序稳定计数
    edge_counts: dict[tuple[str, str], int] = {}
    for src in linked_ids:
        ds = ed_map.get(src, _UNCLASSIFIED)
        for to in graph.out_ids.get(src, []):
            dt = ed_map.get(to, _UNCLASSIFIED)
            if dt == ds:
                continue
            key = (ds, dt) if ds <= dt else (dt, ds)
            edge_counts[key] = edge_counts.get(key, 0) + 1
    edges = [{"from": lo, "to": hi, "count": cnt} for (lo, hi), cnt in sorted(edge_counts.items())]

    return {
        "level": 1,
        "total_entities": len(linked_ids),
        "total_links": sum(out_counts.values()),
        "dynasties": dynasties,
        "edges": edges,
    }


@router.get("/global_by_dynasty/{dynasty_id}")
def global_by_dynasty_detail(
    dynasty_id: str,
    limit: int = Query(40, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    """朝代下钻（level 2）：该朝代 top-N 双链实体子图。

    entities 按 out+in 降序取 [offset, offset+limit)；edges 为返回实体间的
    诱导子图出链（from/to 都在返回集合内）。other_count = total - 已返回累计数。
    __unclassified 同样支持。
    """
    graph = _ensure_graph()
    di = _ensure_dynasty_index()
    ed_map = di.entity_dynasty
    out_counts = {eid: len(outs) for eid, outs in graph.out_ids.items()}
    in_counts = graph.in_counts_occ

    members = []
    for eid, did in ed_map.items():
        if did != dynasty_id:
            continue
        s = out_counts.get(eid, 0) + in_counts.get(eid, 0)
        if s >= 1:
            members.append((s, eid))
    members.sort(key=lambda x: (-x[0], x[1]))

    total = len(members)
    page = members[offset: offset + limit]
    page_ids = {eid for _, eid in page}
    other_count = max(0, total - (offset + len(page)))

    if dynasty_id == _UNCLASSIFIED:
        dynasty_name = "未分类"
    else:
        ent = _INDEX.entity(dynasty_id)
        dynasty_name = ent.get("name") if ent and ent.get("name") else dynasty_id

    entities = []
    for _, eid in page:
        e = _INDEX.entity(eid)
        if not e:
            continue
        entities.append({
            "id": eid,
            "name": e.get("name"),
            "type": e.get("type"),
            "image": e.get("image"),
            "out": out_counts.get(eid, 0),
            "in": in_counts.get(eid, 0),
        })

    edges = []
    seen = set()
    for _, eid in page:
        for to in graph.out_ids.get(eid, []):
            if to in page_ids:
                key = (eid, to)
                if key in seen:
                    continue
                seen.add(key)
                edges.append({"from": eid, "to": to, "type": "wiki_link"})

    return {
        "level": 2,
        "dynasty_id": dynasty_id,
        "dynasty_name": dynasty_name,
        "total": total,
        "other_count": other_count,
        "entities": entities,
        "edges": edges,
    }
