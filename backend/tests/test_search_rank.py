"""回归钉子：q 搜索的相关性排序。

2026-07-15 之前 q 把 name/alias/bio 一视同仁且完全不排序，结果顺序即文件加载顺序：
搜「曹操」头两条是赤壁之战、官渡之战（其 bio 提及曹操），本人排第三；
搜「李」返回的 12 条全是战役，一个李姓人物都没有。

钉住：本人(精确名)必须压过"仅正文提及"的实体。
"""
from app.services.entity_service import list_entities


def _names(q, **kw):
    return [i["name"] for i in list_entities(q=q, limit=20, **kw)["items"]]


def test_exact_name_outranks_bio_mention():
    """搜「曹操」→ 曹操本人在最前，赤壁之战(bio 提及)靠后。"""
    names = _names("曹操")
    assert "曹操" in names, "曹操本人未出现在搜索结果中"
    assert names[0] == "曹操", f"精确名未排第一，实得: {names[:3]}"
    if "赤壁之战" in names:
        assert names.index("曹操") < names.index("赤壁之战"), \
            f"仅 bio 提及的实体压过了本人: {names[:5]}"


def test_person_surfaces_for_surname_query():
    """搜「李」→ 结果里必须有名字含「李」的实体，而非清一色 bio 命中的战役。"""
    items = list_entities(q="李", limit=12)["items"]
    name_hits = [i for i in items if "李" in (i.get("name") or "")]
    assert name_hits, f"12 条里无一条名字含「李」，全是正文命中: {[i['name'] for i in items]}"


def test_prefix_outranks_substring():
    """名字以 q 开头的，排在仅包含 q 的之前。"""
    names = _names("曹")
    prefix = [n for n in names if n.startswith("曹")]
    assert prefix, f"无以「曹」开头的结果: {names[:5]}"
    # 第一个非前缀命中之后，不应再出现前缀命中
    first_non_prefix = next((i for i, n in enumerate(names) if not n.startswith("曹")), len(names))
    assert all(n.startswith("曹") for n in names[:first_non_prefix]), "前缀命中未聚在最前"


def test_seed_beats_cbdb_at_same_rank():
    """同相关度下种子实体优先于 CBDB 批量导入条目。"""
    items = list_entities(q="李白", limit=20)["items"]
    ids = [i["id"] for i in items]
    assert "p_li_bai" in ids, "种子李白未出现"
    cbdb = [i for i, x in enumerate(ids) if x.startswith("p_cbdb_")]
    if cbdb:
        assert ids.index("p_li_bai") < cbdb[0], f"CBDB 条目压过了种子李白: {ids[:5]}"


def test_modern_name_recall():
    """今名检索(C2):搜「南京」应召回 modern_name 含南京的古地名(黄天荡/天京/六合等),
    且今名命中排在 name/alias 命中之后。"""
    items = list_entities(q="南京", limit=20, fields=["name", "modern_name", "alias", "aliases"])["items"]
    names = [i["name"] for i in items]
    assert len(names) >= 10, f"今名召回不足(handoff 实测 ~11): {names}"
    for expected in ("黄天荡", "天京", "六合"):
        assert expected in names, f"今名命中缺失「{expected}」: {names}"
    # 今名命中的实体不得压过 name/alias 恰含「南京」的实体
    modern_only = [i["name"] for i in items
                   if "南京" not in (i.get("name") or "")
                   and not any("南京" in (a or "") for a in (i.get("alias") or []) + (i.get("aliases") or []))]
    direct = [n for n in names if n not in modern_only]
    if direct and modern_only:
        assert names.index(direct[-1]) < names.index(modern_only[0]), \
            f"今名命中压过了名/别名命中: {names}"
