"""索引单元测试：EntityIndex / RelationIndex（backend/app/core/data.py）。"""
import json
import os
from pathlib import Path

import yaml

from app.core.data import EntityIndex, RelationIndex

LI_BAI = "p_li_bai"


def _exact_yaml_value(left, right):
    """对象值、容器顺序和标量类型都必须一致（避免 True == 1 漏报）。"""
    if type(left) is not type(right):
        return False
    if isinstance(left, dict):
        return (list(left) == list(right)
                and all(_exact_yaml_value(left[key], right[key]) for key in left))
    if isinstance(left, list):
        return (len(left) == len(right)
                and all(_exact_yaml_value(a, b) for a, b in zip(left, right)))
    return left == right


def test_csafe_loader_matches_safe_loader_for_every_repository_yaml():
    """LibYAML 快路径对仓库全部 YAML 生成完全相同的 Python 对象。"""
    from app.core import data as data_module

    if not hasattr(yaml, "CSafeLoader"):
        assert data_module._YAML_SAFE_LOADER is yaml.SafeLoader
        return
    assert data_module._YAML_SAFE_LOADER is yaml.CSafeLoader

    repo = Path(__file__).resolve().parents[2]
    paths = sorted((repo / "data").rglob("*.yaml")) + sorted((repo / "schema").glob("*.yaml"))
    assert paths
    for path in paths:
        with path.open(encoding="utf-8") as fh:
            expected = yaml.load(fh, Loader=yaml.SafeLoader)
        with path.open(encoding="utf-8") as fh:
            actual = yaml.load(fh, Loader=data_module._YAML_SAFE_LOADER)
        assert _exact_yaml_value(actual, expected), f"Loader 语义差异：{path}"


def test_entity_and_relation_indices_reload_after_yaml_change(monkeypatch, tmp_path):
    """C loader 不得改变目录签名驱动的实体、关系同步热更新。"""
    from app.core import data as data_module

    entity_dir = tmp_path / "entities" / "persons"
    relation_dir = tmp_path / "relations"
    entity_dir.mkdir(parents=True)
    relation_dir.mkdir()
    entity_path = entity_dir / "sample.yaml"
    relation_path = relation_dir / "sample.yaml"
    entity_path.write_text("id: sample\ntype: Person\nname: 初名\n", encoding="utf-8")
    relation_path.write_text("- from: sample\n  to: target\n  type: knows\n", encoding="utf-8")

    monkeypatch.setattr(data_module.settings, "data_dir", tmp_path)
    monkeypatch.setattr(data_module, "_entity_index", data_module.EntityIndex())
    monkeypatch.setattr(data_module, "_relation_index", data_module.RelationIndex())
    monkeypatch.setattr(data_module, "_cache", {})
    monkeypatch.setattr(data_module, "_index_sig", None)
    monkeypatch.setattr(data_module, "_index_sig_checked_at", 0.0)
    monkeypatch.setattr(data_module, "_SIG_TTL", 0.0)

    assert data_module.load_entity("sample")["name"] == "初名"
    assert data_module.load_all_relations()[0]["type"] == "knows"

    entity_path.write_text("id: sample\ntype: Person\nname: 新名\n", encoding="utf-8")
    relation_path.write_text("- from: sample\n  to: target\n  type: opposes\n", encoding="utf-8")
    # 签名取最新 mtime + 文件数；显式推进 mtime，避免极速文件系统写入落在同一刻度。
    future = max(entity_path.stat().st_mtime, relation_path.stat().st_mtime) + 2
    os.utime(entity_path, (future, future))
    os.utime(relation_path, (future, future))

    assert data_module.load_entity("sample")["name"] == "新名"
    assert data_module.load_all_relations()[0]["type"] == "opposes"


def test_geojson_loader_uses_json_parser_and_cache(monkeypatch, tmp_path):
    """GeoJSON 不得退回慢速 YAML 解析；二次读取复用同一缓存对象。"""
    from app.core import data as data_module

    geo_dir = tmp_path / "geo"
    geo_dir.mkdir()
    expected = {
        "type": "FeatureCollection",
        "features": [{"type": "Feature", "properties": {"name": "测试"},
                      "geometry": {"type": "Point", "coordinates": [120, 30]}}],
    }
    (geo_dir / "sample.geojson").write_text(
        json.dumps(expected, ensure_ascii=False), encoding="utf-8")
    monkeypatch.setattr(data_module.settings, "data_dir", tmp_path)
    monkeypatch.setattr(
        data_module, "_read_yaml",
        lambda _path: (_ for _ in ()).throw(AssertionError("GeoJSON 误走 YAML 解析")),
    )

    index = EntityIndex()
    first = index.get_geojson("sample.geojson")
    second = index.get_geojson("sample.geojson")

    assert first == expected
    assert second is first


def _old_neighbors(relations: list[dict], eid: str, depth: int):
    """改造前的全表扫描算法；用于锁定优化前后语义与边顺序完全一致。"""
    adjacency = {}
    for rel in relations:
        f, t = rel.get("from"), rel.get("to")
        if f and t:
            adjacency.setdefault(f, []).append(t)
            adjacency.setdefault(t, []).append(f)
    if eid not in adjacency:
        return [], []
    visited = {eid}
    frontier = {eid}
    found_edges = []
    for _ in range(depth):
        next_frontier = set()
        for rel in relations:
            f, t = rel.get("from"), rel.get("to")
            if f in frontier and t not in visited:
                found_edges.append(rel)
                next_frontier.add(t)
                visited.add(t)
            elif t in frontier and f not in visited:
                found_edges.append(rel)
                next_frontier.add(f)
                visited.add(f)
        frontier = next_frontier
        if not frontier:
            break
    seen = {(r["from"], r["to"], r["type"]) for r in found_edges}
    for rel in relations:
        key = (rel.get("from"), rel.get("to"), rel.get("type"))
        if (rel.get("from") in visited and rel.get("to") in visited
                and key not in seen):
            found_edges.append(rel)
            seen.add(key)
    return list(visited), found_edges


def test_adjacency_symmetry(relation_index: RelationIndex):
    """邻接对称性：关系 from A to B，则 B 在 A 的邻居里且 A 在 B 的邻居里。"""
    # 找一条 from/to 都存在的关系
    rel = next((r for r in relation_index.relations if r.get("from") and r.get("to")), None)
    assert rel is not None, "无关系数据"
    a, b = rel["from"], rel["to"]
    adj = relation_index.adjacency
    nbrs_a = [n for n, _ in adj.get(a, [])]
    nbrs_b = [n for n, _ in adj.get(b, [])]
    assert b in nbrs_a, f"{b} 不在 {a} 的邻居中"
    assert a in nbrs_b, f"{a} 不在 {b} 的邻居中"


def test_neighbors_indexed_algorithm_matches_previous_semantics():
    """多前沿、环、反向边和平行边下，节点集合与边对象/顺序均不漂移。"""
    relations = [
        {"from": "a", "to": "b", "type": "r0"},
        {"from": "a", "to": "c", "type": "r1"},
        {"from": "c", "to": "d", "type": "r2"},
        {"from": "b", "to": "d", "type": "r3"},
        {"from": "d", "to": "a", "type": "r4"},
        {"from": "b", "to": "c", "type": "cross"},
        {"from": "a", "to": "b", "type": "r0", "note": "parallel"},
        {"from": "e", "to": "f", "type": "isolated"},
    ]
    index = RelationIndex()
    index.build(relations)
    for root in ("a", "b", "e", "missing"):
        for depth in range(5):
            old_nodes, old_edges = _old_neighbors(relations, root, depth)
            new_nodes, new_edges = index.neighbors(root, depth)
            assert set(new_nodes) == set(old_nodes), (root, depth)
            assert new_edges == old_edges, (root, depth)


def test_neighbors_does_not_iterate_full_relation_table_after_build():
    """局部查询只能按下标访问关联边，不得悄悄退回逐层全表扫描。"""
    class CountingList(list):
        iterations = 0

        def __iter__(self):
            self.iterations += 1
            return super().__iter__()

    relations = CountingList([
        {"from": "a", "to": "b", "type": "near"},
        *(
            {"from": f"x{i}", "to": f"y{i}", "type": "far"}
            for i in range(100)
        ),
    ])
    index = RelationIndex()
    index.build(relations)
    relations.iterations = 0

    nodes, edges = index.neighbors("a", depth=4)

    assert set(nodes) == {"a", "b"}
    assert [r["type"] for r in edges] == ["near"]
    assert relations.iterations == 0


def test_shortest_path_self_reflexive(relation_index: RelationIndex):
    """BFS shortest_path 自反(from==to)：不崩溃，不返回伪多跳路径。

    当前实现对 from==to 返回 path=None（因起点已在 visited 中，邻居被跳过）。
    此处断言「结构合法且 path 为 None 或零跳」，把 None 行为作为可疑点报告，不固化。
    """
    sp = relation_index.shortest_path(LI_BAI, LI_BAI, 4)
    assert sp["from"] == LI_BAI
    assert sp["to"] == LI_BAI
    # 自反不应返回多跳路径：path 要么 None，要么空列表
    assert sp.get("path") is None or sp["path"] == []


def test_shortest_path_unreachable(relation_index: RelationIndex):
    """BFS shortest_path 不可达分支：to 不在图中 -> path=None。"""
    sp = relation_index.shortest_path(LI_BAI, "p_does_not_exist_xyz", 4)
    assert sp["path"] is None


def test_shortest_path_connected(relation_index: RelationIndex):
    """BFS shortest_path 成功分支：直接邻居 -> path 非空、depth>=1。

    用李白的某个直接邻居保证一定连通，覆盖「返回路径且跳数≥1」分支。
    """
    adj = relation_index.adjacency
    assert LI_BAI in adj and len(adj[LI_BAI]) > 0, "李白无关系邻居"
    neighbor = adj[LI_BAI][0][0]
    sp = relation_index.shortest_path(LI_BAI, neighbor, 3)
    assert sp["path"] is not None, f"直接邻居 {neighbor} 却无可达路径"
    assert sp["depth"] >= 1
    assert sp["depth"] == len(sp["path"])
