"""YAML data loader with pre-built indices.

启动时一次性加载全部 YAML 并构建多级索引：
  - by_id:        O(1) 实体查找
  - by_type:      O(1) 按类型过滤
  - by_year:      按年份快速过滤（人物生卒 / 政权存续 / 事件年份）
  - relations_adj: 邻接表（关系图查询）

缓存策略：首次加载后存进程内存。通过检查目录 mtime 判断是否需要重新加载。
"""
from pathlib import Path
import json
import os
import time
from .config import settings

# PyYAML 只在本地直读真相源时需要；EdgeOne 运行时读构建期编译的 JSON，
# 因此不应为云函数强制打包 PyYAML。本地 requirements 仍锁定 6.0.2。
try:
    import yaml
except ModuleNotFoundError:  # pragma: no cover - EdgeOne 紧凑 JSON 运行包
    yaml = None

_YAML_SAFE_LOADER = (
    getattr(yaml, "CSafeLoader", yaml.SafeLoader)
    if yaml is not None else None
)

# === 缓存层 ===
_cache: dict = {}
_CACHE_TTL = float(os.getenv("DATA_CACHE_TTL", "0"))  # 0 = 依赖 mtime
_COMPILED_DATA_REQUIRED = os.getenv("COMPILED_DATA_REQUIRED", "0") == "1"
_COMPILED_FILENAMES = (
    "entities.json",
    "relations.json",
    "schema_registry.json",
    "relations_schema.json",
)


def _read_yaml(path: Path) -> dict:
    if yaml is None:
        raise RuntimeError("PyYAML is required when reading source YAML data")
    with open(path, "r", encoding="utf-8") as f:
        return yaml.load(f, Loader=_YAML_SAFE_LOADER) or {}


def _read_json(path: Path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _compiled_manifest() -> dict | None:
    """Return and validate the compiled bundle manifest when present/required."""
    compiled_dir = settings.data_dir / "_compiled"
    manifest_path = compiled_dir / "manifest.json"
    if not manifest_path.exists():
        if _COMPILED_DATA_REQUIRED:
            raise RuntimeError(f"Compiled data manifest is required: {manifest_path}")
        return None
    manifest = _read_json(manifest_path)
    if not isinstance(manifest, dict):
        raise ValueError(f"Compiled manifest must be an object: {manifest_path}")
    missing = [name for name in _COMPILED_FILENAMES if not (compiled_dir / name).is_file()]
    if missing:
        raise RuntimeError(f"Compiled data bundle is incomplete; missing: {', '.join(missing)}")
    return manifest


def _compiled_path(filename: str) -> Path:
    path = settings.data_dir / "_compiled" / filename
    manifest = _compiled_manifest()
    if manifest is not None and not path.is_file():
        raise RuntimeError(f"Compiled data file is required: {path}")
    return path


def _validate_compiled_count(payload: list, key: str, path: Path) -> None:
    manifest = _compiled_manifest()
    expected = manifest.get(key) if manifest else None
    if expected is not None and expected != len(payload):
        raise ValueError(
            f"Compiled {key} mismatch: manifest={expected} actual={len(payload)} path={path}"
        )


def _dir_signature(path: Path) -> tuple:
    """目录签名：(最新 mtime, 文件数)。"""
    manifest = path / "_compiled" / "manifest.json"
    if manifest.exists():
        try:
            payload = _read_json(manifest)
            return (payload.get("content_sha256", ""), payload.get("source_file_count", 0))
        except (OSError, ValueError, TypeError):
            pass
    if not path.exists():
        return (0, 0)
    max_mtime = 0
    count = 0
    for p in path.rglob("*.yaml"):
        try:
            m = p.stat().st_mtime
            if m > max_mtime:
                max_mtime = m
            count += 1
        except OSError:
            pass
    return (max_mtime, count)


def _get_cached(key: str, loader_fn, dir_path: Path):
    """通用缓存：get(key) -> hit 返回；miss 调 loader_fn 并缓存。"""
    global _cache
    sig = _dir_signature(dir_path)
    cached = _cache.get(key)
    if cached and cached["sig"] == sig:
        return cached["data"]
    data = loader_fn()
    _cache[key] = {"sig": sig, "data": data, "ts": time.time()}
    return data


def clear_cache():
    """手动清缓存（数据变更后调）。"""
    global _cache
    _cache.clear()


def reload_all():
    """强制重读磁盘：重建实体/关系索引并清缓存。

    供签名失效路径调用（见 links.py 的 _ensure_index）：EntityIndex / RelationIndex
    单例一旦 _built=True 自身不会重建，数据文件改动后必须显式重置才能读到新数据。
    """
    _entity_index._built = False
    _entity_index.build()
    _relation_index._built = False
    _relation_index.build()
    _cache.clear()


# === Schema ===

def load_schema_registry() -> dict[str, dict]:
    compiled = _compiled_path("schema_registry.json")
    if compiled.exists():
        return _get_cached("schema_registry", lambda: _read_json(compiled), settings.data_dir)

    def _load():
        registry = {}
        for path in sorted(settings.schema_dir.glob("*.yaml")):
            if path.name.startswith("_") or path.name == "relations.yaml":
                continue
            data = _read_yaml(path)
            if "type" in data:
                registry[data["type"]] = data
        return registry
    return _get_cached("schema_registry", _load, settings.schema_dir)


def load_relations_schema() -> list[dict]:
    compiled = _compiled_path("relations_schema.json")
    if compiled.exists():
        return _read_json(compiled)
    path = settings.schema_dir / "relations.yaml"
    if not path.exists():
        return []
    data = _read_yaml(path)
    return data.get("relations", [])


# === Entities with indices ===

class EntityIndex:
    """预建索引的实体存储。"""

    def __init__(self):
        self._entities: list[dict] = []
        self._by_id: dict[str, dict] = {}
        self._by_type: dict[str, list[dict]] = {}
        self._persons_by_year: list[dict] = []  # 按 born 排序
        self._polities: list[dict] = []
        self._geojson_cache: dict[str, dict] = {}
        self._built = False

    def build(self, entities: list[dict] | None = None):
        if entities is None:
            entities = _load_all_entities_raw()
        self._entities = entities
        self._by_id = {}
        self._by_type = {}
        self._persons_by_year = []
        self._polities = []

        for e in entities:
            eid = e.get("id")
            if not eid:
                continue
            self._by_id[eid] = e
            t = e.get("type", "unknown")
            self._by_type.setdefault(t, []).append(e)
            if t == "Person":
                born = (e.get("born") or {}).get("year")
                if born is not None:
                    self._persons_by_year.append(e)
            elif t == "Polity":
                self._polities.append(e)

        self._persons_by_year.sort(
            key=lambda p: (p.get("born") or {}).get("year", 0)
        )
        self._built = True

    @property
    def entities(self) -> list[dict]:
        if not self._built:
            self.build()
        return self._entities

    @property
    def by_id(self) -> dict[str, dict]:
        if not self._built:
            self.build()
        return self._by_id

    @property
    def by_type(self) -> dict[str, list[dict]]:
        if not self._built:
            self.build()
        return self._by_type

    def get(self, eid: str) -> dict | None:
        if not self._built:
            self.build()
        return self._by_id.get(eid)

    def persons_alive_at(self, year: int, limit: int | None = 200, offset: int = 0) -> list[dict]:
        """O(log N) 二分查找在世人物。limit=None 表示不截断，返回该年全部在世者。

        注意扫描方向是**从生年最晚者往回**，所以截断丢的永远是最年长的那批 ——
        而年长者恰恰最可能是当年的重量级人物。调用方若要按重要性/种子性排序，
        必须传 limit=None 自己排完再切；先截断后排序救不回没进池子的人。
        实测代价：limit=230 → 0.13ms，不截断 → 0.20ms（born_years 每次都要重建，
        本来就是 O(N)，break 省不下量级）。
        """
        if not self._built:
            self.build()
        import bisect
        # 二分找到 born <= year 的区间
        born_years = [((p.get("born") or {}).get("year", 0)) for p in self._persons_by_year]
        right = bisect.bisect_right(born_years, year)
        cap = None if limit is None else limit + offset
        result = []
        for i in range(right - 1, -1, -1):
            p = self._persons_by_year[i]
            died = (p.get("died") or {}).get("year")
            if died is None or died >= year:
                result.append(p)
                if cap is not None and len(result) >= cap:
                    break
        return result[offset:] if limit is None else result[offset:offset + limit]

    def entities_by_type(self, etype: str) -> list[dict]:
        if not self._built:
            self.build()
        return self._by_type.get(etype, [])

    def get_geojson(self, filename: str) -> dict | None:
        if not filename:
            return None
        if filename in self._geojson_cache:
            return self._geojson_cache[filename]
        path = settings.data_dir / "geo" / filename
        if not path.exists():
            return None
        # GeoJSON 是严格 JSON；用 yaml.safe_load 解析 12MB CHGIS 首次聚合实测约
        # 18 秒，而标准库 json.load 为亚秒级。两者返回结构相同，不应让通用 YAML
        # 入口拖慢地图首个疆域请求。
        with open(path, "r", encoding="utf-8") as file:
            data = json.load(file)
        self._geojson_cache[filename] = data
        return data


def _load_all_entities_raw() -> list[dict]:
    compiled = _compiled_path("entities.json")
    if compiled.exists():
        data = _read_json(compiled)
        if not isinstance(data, list):
            raise ValueError(f"Compiled entities must be a list: {compiled}")
        _validate_compiled_count(data, "entity_count", compiled)
        return data
    entities = []
    entities_dir = settings.data_dir / "entities"
    if not entities_dir.exists():
        return entities
    for type_dir in sorted(entities_dir.iterdir()):
        if not type_dir.is_dir():
            continue
        for path in sorted(type_dir.glob("*.yaml")):
            try:
                data = _read_yaml(path)
                if data and "type" in data:
                    entities.append(data)
            except Exception:
                pass
    return entities


# === Module-level singleton ===

_entity_index = EntityIndex()

# 索引失效追踪：改数据后自动重建。原实现 _built 一旦 True 永不重建，改 YAML 后
# 必须重启后端才能读到新数据（reign/roles/spacetime links 均因此反复踩坑，也坑用户）。
# _dir_signature 要 rglob 7000+ 文件较重，故用 TTL 节流：热路径仅在距上次检查超过
# _SIG_TTL 秒时才重新 stat 目录签名，签名变化才 reload_all（重建实体/关系索引+清缓存）。
_index_sig: tuple | None = None
_index_sig_checked_at: float = 0.0
_SIG_TTL = 2.0


def _ensure_index():
    global _index_sig, _index_sig_checked_at
    if not _entity_index._built:
        _entity_index.build()
        _index_sig = _dir_signature(settings.data_dir)
        _index_sig_checked_at = time.time()
        return
    now = time.time()
    if now - _index_sig_checked_at < _SIG_TTL:
        return
    _index_sig_checked_at = now
    sig = _dir_signature(settings.data_dir)
    if sig != _index_sig:
        reload_all()
        _index_sig = sig


def load_all_entities() -> list[dict]:
    _ensure_index()
    return _entity_index.entities


def load_entity(eid: str) -> dict | None:
    _ensure_index()
    return _entity_index.get(eid)


def load_entities_by_type(etype: str) -> list[dict]:
    _ensure_index()
    return _entity_index.entities_by_type(etype)


def load_persons_alive(year: int, limit: int | None = 200, offset: int = 0) -> list[dict]:
    _ensure_index()
    return _entity_index.persons_alive_at(year, limit, offset)


# === Relations with adjacency index ===

class RelationIndex:
    """预建邻接表的关系存储。"""

    def __init__(self):
        self._relations: list[dict] = []
        self._adjacency: dict[str, list[tuple[str, dict]]] = {}
        # entity id -> 原始关系数组下标。neighbors 既要只访问局部边，又要保持旧实现
        # “逐层按 YAML/文件装载顺序扫描”的稳定选择与返回顺序，因此不能只遍历
        # adjacency（多前沿节点时会随 set 顺序漂移）。
        self._incident: dict[str, list[int]] = {}
        self._built = False

    def build(self, relations: list[dict] | None = None):
        if relations is None:
            relations = _load_all_relations_raw()
        self._relations = relations
        self._adjacency = {}
        self._incident = {}
        for idx, r in enumerate(relations):
            f, t = r.get("from"), r.get("to")
            if f and t:
                self._adjacency.setdefault(f, []).append((t, r))
                self._adjacency.setdefault(t, []).append((f, r))
                self._incident.setdefault(f, []).append(idx)
                self._incident.setdefault(t, []).append(idx)
        self._built = True

    @property
    def relations(self) -> list[dict]:
        if not self._built:
            self.build()
        return self._relations

    @property
    def adjacency(self) -> dict[str, list[tuple[str, dict]]]:
        if not self._built:
            self.build()
        return self._adjacency

    def neighbors(self, eid: str, depth: int = 1) -> tuple[list[dict], list[dict]]:
        """BFS 返回 (nodes, edges)。"""
        if not self._built:
            self.build()
        if eid not in self.adjacency:
            return [], []
        visited = {eid}
        frontier = {eid}
        found_edges = []
        for _ in range(depth):
            next_frontier = set()
            # 同一关系可能同时邻接两个前沿节点；先去重再按全局关系顺序排，等价于
            # 旧版每一层完整扫描 _relations，但成本只随前沿的关联边增长。
            edge_indexes = sorted({
                idx
                for node in frontier
                for idx in self._incident.get(node, ())
            })
            for idx in edge_indexes:
                r = self._relations[idx]
                f, t = r.get("from"), r.get("to")
                if f in frontier and t not in visited:
                    found_edges.append(r)
                    next_frontier.add(t)
                    visited.add(t)
                elif t in frontier and f not in visited:
                    found_edges.append(r)
                    next_frontier.add(f)
                    visited.add(f)
            frontier = next_frontier
            if not frontier:
                break
        # 补充已访问节点间的边
        seen = {(r["from"], r["to"], r["type"]) for r in found_edges}
        visited_edge_indexes = sorted({
            idx
            for node in visited
            for idx in self._incident.get(node, ())
        })
        for idx in visited_edge_indexes:
            r = self._relations[idx]
            key = (r.get("from"), r.get("to"), r.get("type"))
            if (r.get("from") in visited and r.get("to") in visited
                    and key not in seen):
                found_edges.append(r)
                seen.add(key)
        return list(visited), found_edges

    def shortest_path(self, from_id: str, to_id: str, max_depth: int = 4) -> dict:
        """BFS 最短路径。"""
        if not self._built:
            self.build()
        if from_id not in self.adjacency or to_id not in self.adjacency:
            return {"from": from_id, "to": to_id, "path": None}
        from collections import deque
        visited = {from_id}
        queue = deque([(from_id, [])])
        while queue:
            node, path = queue.popleft()
            if len(path) >= max_depth:
                continue
            for next_node, rel in self.adjacency.get(node, []):
                if next_node in visited:
                    continue
                visited.add(next_node)
                new_path = path + [{
                    "from": rel["from"], "to": rel["to"],
                    "type": rel["type"],
                    "since": rel.get("since"), "until": rel.get("until"),
                    "note": rel.get("note"),
                }]
                if next_node == to_id:
                    return {"from": from_id, "to": to_id, "depth": len(new_path), "path": new_path}
                queue.append((next_node, new_path))
        return {"from": from_id, "to": to_id, "path": None}


def _load_all_relations_raw() -> list[dict]:
    compiled = _compiled_path("relations.json")
    if compiled.exists():
        data = _read_json(compiled)
        if not isinstance(data, list):
            raise ValueError(f"Compiled relations must be a list: {compiled}")
        _validate_compiled_count(data, "relation_count", compiled)
        return data
    relations = []
    rel_dir = settings.data_dir / "relations"
    if not rel_dir.exists():
        return relations
    for path in sorted(rel_dir.glob("*.yaml")):
        try:
            data = _read_yaml(path)
            if isinstance(data, list):
                relations.extend(data)
            elif isinstance(data, dict) and "relations" in data:
                relations.extend(data["relations"])
        except Exception:
            pass
    return relations


_relation_index = RelationIndex()


def load_all_relations() -> list[dict]:
    if not _relation_index._built:
        _relation_index.build()
    return _relation_index.relations


def get_relation_index() -> RelationIndex:
    if not _relation_index._built:
        _relation_index.build()
    return _relation_index


def get_entity_index() -> EntityIndex:
    _ensure_index()
    return _entity_index


def load_geojson(filename: str) -> dict | None:
    _ensure_index()
    return _entity_index.get_geojson(filename)
