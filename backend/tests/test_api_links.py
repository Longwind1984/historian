"""API 合同测试：/api/links/*。"""
from concurrent.futures import ThreadPoolExecutor
import time

from fastapi.testclient import TestClient

LI_BAI = "p_li_bai"


def _reference_scan_dual(text, names):
    """优化前逐名字 `str.find` 实现；只用于锁定完全相同的扫描语义。"""
    occupied = [False] * len(text)
    occupied_hits = []
    all_hits = []
    for name, eid in names:
        start = 0
        while True:
            idx = text.find(name, start)
            if idx < 0:
                break
            end = idx + len(name)
            all_hits.append((idx, eid, name))
            if not any(occupied[idx:end]):
                for pos in range(idx, end):
                    occupied[pos] = True
                occupied_hits.append({
                    "id": eid,
                    "name": name,
                    "offset": idx,
                    "length": len(name),
                })
            start = end
    occupied_hits.sort(key=lambda mention: mention["offset"])
    return occupied_hits, all_hits


def test_trie_scan_matches_reference_for_every_corpus_text_field():
    """全库逐字段对照旧算法，防止优化改变重叠、同名或排序语义。"""
    from app.api import links

    links._ensure_index()
    names = links._INDEX.names
    for entity in links._INDEX._entities_by_id.values():
        for field in links.TEXT_FIELDS:
            text = entity.get(field)
            if not isinstance(text, str) or not text:
                continue
            expected = _reference_scan_dual(text, names)
            actual = links._scan_dual(text)
            assert actual == expected, f"{entity['id']}.{field} 扫描语义发生变化"


def test_trie_scan_preserves_overlap_and_duplicate_name_semantics(monkeypatch):
    """覆盖语料未必包含的自重叠、长短重叠和同名多实体边界。"""
    from app.api import links

    index = links.NameIndex()
    index.build([
        {"id": "repeat", "name": "哈哈"},
        {"id": "long", "name": "甲乙丙"},
        {"id": "short", "name": "甲乙"},
        {"id": "same_a", "name": "同名"},
        {"id": "same_b", "name": "同名"},
    ])
    monkeypatch.setattr(links, "_INDEX", index)

    for text in ("哈哈哈", "甲乙丙甲乙", "同名同名", "甲乙丙同名哈哈哈"):
        assert links._scan_dual(text) == _reference_scan_dual(text, index.names)


def test_mention_graph_cold_build_is_single_flight(monkeypatch):
    """并发首次访问只允许一个线程冷建 MentionGraph。"""
    from app.api import links

    class FakeGraph:
        def __init__(self):
            self._built = False
            self._sig = None
            self.build_count = 0

        def build(self, _index):
            self.build_count += 1
            time.sleep(0.05)  # 放大三个请求同时越过冷建检查的竞争窗口
            self._built = True

    graph = FakeGraph()
    monkeypatch.setattr(links, "_GRAPH", graph)
    monkeypatch.setattr(links, "_ensure_index", lambda: "test-signature")

    with ThreadPoolExecutor(max_workers=3) as pool:
        results = list(pool.map(lambda _: links._ensure_graph(), range(3)))

    assert results == [graph, graph, graph]
    assert graph.build_count == 1
    assert graph._sig == "test-signature"


def test_links_scan(client: TestClient):
    """/api/links/scan/{id}：返回出链提及结构。"""
    r = client.get(f"/api/links/scan/{LI_BAI}")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["entity_id"] == LI_BAI
    assert body["count"] == len(body["mentions"])
    for m in body["mentions"]:
        assert "to_id" in m and "to_name" in m and "field" in m


def test_links_backlinks(client: TestClient):
    """/api/links/backlinks/{id}：返回入链结构。"""
    r = client.get(f"/api/links/backlinks/{LI_BAI}")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["entity_id"] == LI_BAI
    assert body["count"] == len(body["backlinks"])
    for b in body["backlinks"]:
        assert "from_id" in b and "from_name" in b


def test_links_count(client: TestClient):
    """/api/links/count/{id}：返回出/入链计数。"""
    r = client.get(f"/api/links/count/{LI_BAI}")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["entity_id"] == LI_BAI
    assert isinstance(body["outbound"], int)
    assert isinstance(body["inbound"], int)


def test_links_search(client: TestClient):
    """/api/links/search?q=李白：命中李白本人。"""
    r = client.get("/api/links/search", params={"q": "李白"})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["q"] == "李白"
    assert body["count"] >= 1
    ids = [h["id"] for h in body["hits"]]
    assert LI_BAI in ids, f"搜索「李白」未命中 p_li_bai: {ids[:5]}"


def test_links_global(client: TestClient):
    """/api/links/global?limit=50&min_links=2：全局图，node_count ≤ limit。"""
    r = client.get("/api/links/global", params={"limit": 50, "min_links": 2})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["node_count"] <= 50, f"node_count={body['node_count']} 超过 limit=50"
    assert body["node_count"] >= 1
    assert isinstance(body["nodes"], list)
    assert isinstance(body["edges"], list)
    # node_count 与 nodes 列表一致
    assert body["node_count"] == len(body["nodes"])


def test_links_global_by_dynasty(client: TestClient):
    """/api/links/global_by_dynasty：朝代聚合 level-1 视图。"""
    r = client.get("/api/links/global_by_dynasty")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["level"] == 1
    assert "dynasties" in body and "edges" in body
    ids = [d["id"] for d in body["dynasties"]]
    assert "__unclassified" in ids, f"未分类节点缺失: {ids}"
    assert len(body["dynasties"]) <= 20
    for d in body["dynasties"]:
        assert d["entity_count"] >= 0
        assert d["link_count"] >= 0
    # level-2 下钻：未分类节点也应可查
    r2 = client.get("/api/links/global_by_dynasty/__unclassified", params={"limit": 5})
    assert r2.status_code == 200, r2.text
    b2 = r2.json()
    assert b2["level"] == 2
    assert b2["dynasty_id"] == "__unclassified"
    assert isinstance(b2["entities"], list)
    assert b2["other_count"] >= 0
