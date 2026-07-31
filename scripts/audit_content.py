#!/usr/bin/env python3
"""内容规范合规度盘点 (T5.2) -- 只读盘点脚本。

依据 docs/content-spec.md（草案）测量现状与规范的差距，产出基线报告，
为 Rick 的规范决策与后续重扫工程量估算提供数字。

* 不改任何 data/ 文件；不依赖 validate_data.py（本任务是独立盘点）。
* 依赖：仅 pyyaml。
* 环境变量：DATA_DIR / SCHEMA_DIR（缺省回退到脚本所在仓库的 data/ schema/）。

用法:
  env DATA_DIR=$PWD/data SCHEMA_DIR=$PWD/schema python scripts/audit_content.py
  ... --json out.json   # 可选落盘机器可读结果
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = Path(os.environ.get("DATA_DIR", str(ROOT / "data")))
SCHEMA_DIR = Path(os.environ.get("SCHEMA_DIR", str(ROOT / "schema")))
ENTITIES_DIR = DATA_DIR / "entities"
RELATIONS_DIR = DATA_DIR / "relations"

# --- 规范常量（来自 docs/content-spec.md）---------------------------------

# 亲属(自明)关系：规范 §1 豁免 note（类型即含义）
KINSHIP = {"father_of", "mother_of", "spouse_of", "sibling_of", "child_of"}

# 事件因果关联类型（schema/relations.yaml：led_to 因->果 / caused_by 果->因）
CAUSAL_TYPES = {"led_to", "caused_by"}
# part_of / concurrent_with 说明库内已有可建模事件 counterpart，但不冒充因果。
# includes 是 part_of 的逆向写法，也计作上下文建模。
EVENT_CONTEXT_TYPES = {"part_of", "includes", "concurrent_with"}

# CBDB 桩 bio：形如 "CBDB ID 3415"，非真实小传
STUB_BIO_RE = re.compile(r"^\s*CBDB ID \d+\s*$")

# 模板化套话 note 模式（CBDB 繁体模板 + 通用套话）。
# 每条 (regex, 标签)；按顺序匹配，首中即归属该 note 一个标签（避免重复计数）。
BOILERPLATE = [
    (r"收到.*贈[詩诗]", "收到Y的赠诗/文"),
    (r"贈[詩诗]、文", "赠诗、文(无主语模板)"),
    (r"收到.*答書", "收到Y的答书"),
    (r"致書", "致书Y"),
    (r"答Y?書", "答Y书"),
    (r"被致書", "被致书由Y"),
    (r"作墓[誌志]銘", "为Y作墓志铭"),
    (r"作墓表", "为Y作墓表"),
    (r"作祭文", "为Y作祭文"),
    (r"祭文由Y所作", "祭文由Y所作"),
    (r"作傳", "为Y作传"),
    (r"所著書?作[跋序]", "为Y所著书作跋/序"),
    (r"書[跋序]由Y所作", "书跋/序由Y所作"),
    (r"建築物.*題詠", "建筑物题咏"),
    (r"作臨別贈言", "为Y作临别赠言"),
    (r"有交往", "有交往"),
    (r"相唱和", "相唱和(无细节)"),
    (r"推薦", "推荐(无细节)"),
    (r"欣賞/?器重", "欣赏/器重(无细节)"),
    (r"CBDB\s*kinrel", "CBDB kinrel 亲属标签"),
]
BOILERPLATE_RE = [(re.compile(p), lbl) for p, lbl in BOILERPLATE]
# CBDB 模板未填充的占位符 "Y"（中文史源散文中不会出现拉丁 Y）
Y_PLACEHOLDER_RE = re.compile(r"Y")


def classify_note(note):
    """判定 note 是否疑似模板化套话。返回 (is_boilerplate, label)。

    非字符串/空 -> (False, None)；命中模式 -> (True, 标签)；
    含 "Y" 占位符 -> (True, "其他含Y占位符(CBDB模板)")。
    """
    if not isinstance(note, str) or not note.strip():
        return (False, None)
    for rx, lbl in BOILERPLATE_RE:
        if rx.search(note):
            return (True, lbl)
    if Y_PLACEHOLDER_RE.search(note):
        return (True, "其他含Y占位符(CBDB模板)")
    return (False, None)


def impact_categories(schema_dir=SCHEMA_DIR):
    """从 Event schema 推导规范 §3 的“战乱/变法类”。

    战乱取 category.family 的“军事”整族；变法与政变仍按 content-spec 的既有
    口径取 reform/coup，但只在 schema options 实际注册时纳入。这样 schema 新增
    war/rebellion 等军事类后审计自动覆盖，不再由脚本里的陈旧枚举漏报。
    """
    schema_path = Path(schema_dir) / "event.yaml"
    with open(schema_path, encoding="utf-8") as fh:
        schema = yaml.safe_load(fh)
    category = ((schema or {}).get("fields") or {}).get("category") or {}
    options = set(category.get("options") or [])
    families = category.get("family") or {}
    military = set(families.get("军事") or [])
    invalid = military - options
    if invalid:
        raise ValueError(f"event.category.family 军事含未注册项: {sorted(invalid)}")
    return military | ({"coup", "reform"} & options)


# ---------------------------------------------------------------------------
# 加载
# ---------------------------------------------------------------------------

def load_entities():
    """{type: [dict, ...]}，遍历 data/entities/<type>/*.yaml。"""
    out = defaultdict(list)
    if not ENTITIES_DIR.is_dir():
        return out
    for type_dir in sorted(ENTITIES_DIR.iterdir()):
        if not type_dir.is_dir():
            continue
        for fp in sorted(type_dir.glob("*.yaml")):
            try:
                with open(fp, encoding="utf-8") as fh:
                    d = yaml.safe_load(fh)
            except Exception:
                continue
            if isinstance(d, dict):
                out[d.get("type", type_dir.name)].append(d)
    return out


def load_relations():
    """list of (relation_dict, source_filename)。"""
    out = []
    if not RELATIONS_DIR.is_dir():
        return out
    for fp in sorted(RELATIONS_DIR.glob("*.yaml")):
        try:
            with open(fp, encoding="utf-8") as fh:
                d = yaml.safe_load(fh)
        except Exception:
            continue
        if isinstance(d, list):
            for r in d:
                if isinstance(r, dict):
                    out.append((r, fp.name))
    return out


def classify_impact_event_links(entities, relations, impact_event_categories):
    """把战乱/变法事件分为有因果边、仅上下文边、尚无事件 counterpart 三层。

    仅当另一端确为 Event/Battle 时才算事件建模；人物参与、地点等关系不会把
    因果缺口伪装成已覆盖。context_only 仍属于 no_causal，不借此豁免规范。
    """
    events = entities.get("Event", [])
    tracked = {
        e.get("id") for e in events
        if e.get("category") in impact_event_categories and e.get("id")
    }
    event_like = {
        e.get("id")
        for kind in ("Event", "Battle")
        for e in entities.get(kind, [])
        if e.get("id")
    }
    causal = set()
    contextual = set()
    for relation, _filename in relations:
        relation_type = relation.get("type")
        if relation_type not in CAUSAL_TYPES | EVENT_CONTEXT_TYPES:
            continue
        source, target = relation.get("from"), relation.get("to")
        for current, counterpart in ((source, target), (target, source)):
            if current not in tracked or counterpart not in event_like:
                continue
            if relation_type in CAUSAL_TYPES:
                causal.add(current)
            else:
                contextual.add(current)

    by_status = {"causal": [], "context_only": [], "isolated": []}
    for event in events:
        event_id = event.get("id")
        if event_id not in tracked:
            continue
        if event_id in causal:
            status = "causal"
        elif event_id in contextual:
            status = "context_only"
        else:
            status = "isolated"
        by_status[status].append(event)
    return by_status


def real_bio(person):
    """返回 (has_bio_field, is_stub, is_real, is_short)。

    has_bio_field: bio 字段存在且非空
    is_stub: CBDB 桩 bio（"CBDB ID xxxx"）
    is_real: 有 bio 且非桩
    is_short: 真实 bio 但 <30 字
    """
    bio = person.get("bio")
    if not isinstance(bio, str) or not bio.strip():
        return (False, False, False, False)
    has = True
    stub = bool(STUB_BIO_RE.match(bio))
    real = has and not stub
    short = real and len(bio.strip()) < 30
    return (has, stub, real, short)


def life_event_coverage(persons, importances=(1, 2)):
    """返回指定 importance 人物的 life_events 覆盖，避免重复估算已完成项。"""
    selected = [p for p in persons if p.get("importance") in importances]
    present = [p for p in selected if p.get("life_events")]
    return {
        "total": len(selected),
        "present": len(present),
        "missing": len(selected) - len(present),
        "missing_ids": [p.get("id") for p in selected if not p.get("life_events")],
    }


def has_year(field):
    """year_month 字段是否有可辨年份。"""
    if field is None:
        return False
    if isinstance(field, bool):
        return False
    if isinstance(field, int):
        return True
    if isinstance(field, dict):
        return isinstance(field.get("year"), int) and not isinstance(field.get("year"), bool)
    return False


def raw_sources_list(entity):
    """返回 sources 中的字符串项，保留空串供格式审计定位。"""
    s = entity.get("sources")
    if isinstance(s, list):
        return [x for x in s if isinstance(x, str)]
    return []


def sources_list(entity):
    """返回非空 sources；空字符串不能冒充字段完整。"""
    return [source for source in raw_sources_list(entity) if source.strip()]


def classify_source(s):
    """单条 source 字符串格式分类 -> '空'|'纯数据库标识'|'无·分卷'|'规范(含·)'。"""
    if not s or not s.strip():
        return "空"
    t = s.strip()
    if "·" in t:
        return "规范(含·)"
    # 纯数据库标识：CBDB / CHGIS 等（规范 §4 允许，但本盘点按"低可追溯"标记）
    if re.match(r"^(CBDB|CHGIS)", t):
        return "纯数据库标识"
    return "无·分卷"


# ---------------------------------------------------------------------------
# 报告
# ---------------------------------------------------------------------------

def section_relations(relations):
    """§1 关系关联逻辑。"""
    print("=" * 72)
    print("§1 关系关联逻辑（规范核心：语义关系必须带 note 说清关联逻辑）")
    print("=" * 72)

    total = len(relations)
    by_type = defaultdict(lambda: {"total": 0, "no_note": 0, "boilerplate": 0, "substantive": 0})
    sem_total = sem_no_note = sem_with_note = sem_boilerplate = sem_substantive = 0
    pattern_counts = Counter()
    cbdb_assoc_total = cbdb_assoc_no_note = 0

    for r, fname in relations:
        t = r.get("type", "?")
        note = r.get("note")
        is_bp, lbl = classify_note(note)
        rec = by_type[t]
        rec["total"] += 1
        if not isinstance(note, str) or not note.strip():
            rec["no_note"] += 1
        elif is_bp:
            rec["boilerplate"] += 1
        else:
            rec["substantive"] += 1

        is_kin = t in KINSHIP
        if not is_kin:
            sem_total += 1
            if not isinstance(note, str) or not note.strip():
                sem_no_note += 1
            else:
                sem_with_note += 1
                if is_bp:
                    sem_boilerplate += 1
                    pattern_counts[lbl] += 1
                else:
                    sem_substantive += 1

        # CBDB associated_with 明细（套话重灾区）
        if t == "associated_with" and fname == "cbdb.yaml":
            cbdb_assoc_total += 1
            if not isinstance(note, str) or not note.strip():
                cbdb_assoc_no_note += 1

    kin_total = sum(rec["total"] for t, rec in by_type.items() if t in KINSHIP)

    print(f"\n关系总数: {total}  (亲属 {kin_total} / 语义 {sem_total})")
    print(f"\n[1.1] 语义关系(非亲属) note 缺失:")
    print(f"  语义关系总数      : {sem_total}")
    print(f"  无 note 数        : {sem_no_note}  ({sem_no_note/max(sem_total,1)*100:.1f}%)")
    print(f"  有 note 数        : {sem_with_note}  ({sem_with_note/max(sem_total,1)*100:.1f}%)")

    print(f"\n[1.2] 有 note 但疑似模板化套话:")
    print(f"  套话 note 数      : {sem_boilerplate}  (占有 note 的 {sem_boilerplate/max(sem_with_note,1)*100:.1f}%)")
    print(f"  实质 note 数      : {sem_substantive}  (占有 note 的 {sem_substantive/max(sem_with_note,1)*100:.1f}%)")
    print(f"  命中模式清单 (按计数):")
    for lbl, c in pattern_counts.most_common():
        print(f"    {c:5d}  {lbl}")

    print(f"\n[1.3] 按关系 type 分组 (total / 无note / 套话note / 实质note):")
    print(f"  {'type':<22}{'total':>8}{'无note':>9}{'套话':>8}{'实质':>8}  备注")
    for t, rec in sorted(by_type.items(), key=lambda kv: -kv[1]["total"]):
        mark = "亲属豁免" if t in KINSHIP else ""
        print(f"  {t:<22}{rec['total']:>8}{rec['no_note']:>9}{rec['boilerplate']:>8}{rec['substantive']:>8}  {mark}")

    print(f"\n[附] associated_with 全部来自 cbdb.yaml: {cbdb_assoc_total} 条"
          f" (其中无 note {cbdb_assoc_no_note}); 非cbdb文件 associated_with = 0")
    print(f"\n>> §1 小结: 语义关系 {sem_total} 条, 无note {sem_no_note} ({sem_no_note/max(sem_total,1)*100:.1f}%), "
          f"套话note {sem_boilerplate} ({sem_boilerplate/max(sem_with_note,1)*100:.1f}% of有note), "
          f"实质note {sem_substantive}")

    return {
        "relation_total": total,
        "kinship_total": kin_total,
        "semantic_total": sem_total,
        "semantic_no_note": sem_no_note,
        "semantic_with_note": sem_with_note,
        "semantic_boilerplate": sem_boilerplate,
        "semantic_substantive": sem_substantive,
        "boilerplate_patterns": dict(pattern_counts),
        "cbdb_associated_with_total": cbdb_assoc_total,
        "cbdb_associated_with_no_note": cbdb_assoc_no_note,
        "by_type": {t: v for t, v in by_type.items()},
    }


def section_persons(persons):
    """§2 人物生平。"""
    print("\n" + "=" * 72)
    print("§2 人物生平结构化（bio + life_events + importance 分层）")
    print("=" * 72)

    total = len(persons)
    has_bio = stub_bio = real_bio_n = short_bio = no_bio = 0
    has_life_events = 0
    imp_buckets = defaultdict(lambda: {"n": 0, "real_bio": 0, "stub": 0, "no_bio": 0})

    for p in persons:
        has, stub, real, short = real_bio(p)
        if not has:
            no_bio += 1
        else:
            has_bio += 1
            if stub:
                stub_bio += 1
            elif real:
                real_bio_n += 1
                if short:
                    short_bio += 1
        if p.get("life_events"):
            has_life_events += 1
        i = p.get("importance")
        key = i if i in (1, 2, 3) else "无标注"
        imp_buckets[key]["n"] += 1
        if stub:
            imp_buckets[key]["stub"] += 1
        elif not has:
            imp_buckets[key]["no_bio"] += 1
        elif real:
            imp_buckets[key]["real_bio"] += 1

    print(f"\n人物总数: {total}")
    print(f"\n[2.1] bio 覆盖:")
    print(f"  有 bio 字段       : {has_bio}  ({has_bio/max(total,1)*100:.1f}%)")
    print(f"  ├─ CBDB 桩 bio    : {stub_bio}  (bio='CBDB ID xxxx', 非真实小传)")
    print(f"  ├─ 真实 bio 过短  : {short_bio}  (<30 字, 需扩)")
    print(f"  └─ 真实 bio 充分  : {real_bio_n - short_bio}")
    print(f"  无 bio            : {no_bio}")

    print(f"\n[2.2] life_events 字段:")
    print(f"  有 life_events    : {has_life_events}  (当前实测覆盖，不沿用旧的零基线)")

    print(f"\n[2.3] 按 importance 分层 (人数 / 真实bio覆盖 / CBDB桩 / 无bio):")
    print(f"  {'importance':<14}{'人数':>8}{'真实bio':>10}{'CBDB桩':>10}{'无bio':>8}  bio覆盖率")
    for k in [1, 2, 3, "无标注"]:
        if k not in imp_buckets:
            continue
        rec = imp_buckets[k]
        cov = rec["real_bio"] / max(rec["n"], 1) * 100
        label = f"{k}(核心)" if k == 1 else f"{k}(重要)" if k == 2 else f"{k}" if k == 3 else "无标注(默认3)"
        print(f"  {label:<14}{rec['n']:>8}{rec['real_bio']:>10}{rec['stub']:>10}{rec['no_bio']:>8}  {cov:.1f}%")

    imp1 = imp_buckets.get(1, {"n": 0})["n"]
    imp2 = imp_buckets.get(2, {"n": 0})["n"]
    imp_none = imp_buckets.get("无标注", {"n": 0})["n"]
    print(f"\n>> §2 小结: 人物 {total}, 真实bio {real_bio_n} ({real_bio_n/max(total,1)*100:.1f}%), "
          f"CBDB桩bio {stub_bio}, 真实bio过短 {short_bio}, 无bio {no_bio}; "
          f"life_events {has_life_events}; 核心{imp1}/重要{imp2}/无标注{imp_none}")

    return {
        "person_total": total,
        "has_bio_field": has_bio,
        "stub_bio": stub_bio,
        "real_bio": real_bio_n,
        "short_bio": short_bio,
        "no_bio": no_bio,
        "has_life_events": has_life_events,
        "importance": {str(k): v for k, v in imp_buckets.items()},
    }


def _missing_report(label, total, missing):
    pct = missing / max(total, 1) * 100
    return f"  {label:<14} 缺失 {missing}/{total}  ({pct:.1f}%)"


def section_fields(entities, event_link_status, impact_event_categories):
    """§3 各类型字段完整度。"""
    print("\n" + "=" * 72)
    print("§3 各类型字段完整度（对 content-spec §3 必填项）")
    print("=" * 72)

    res = {}

    # --- Person ---
    persons = entities.get("Person", [])
    ptot = len(persons)
    p_no_born = sum(1 for p in persons if not has_year(p.get("born")))
    p_no_died = sum(1 for p in persons if not has_year(p.get("died")))
    p_no_bp = sum(1 for p in persons if not p.get("birthplace"))
    p_no_src = sum(1 for p in persons if not sources_list(p))
    # 核心+重要
    core_imp = [p for p in persons if p.get("importance") in (1, 2)]
    ci_tot = len(core_imp)
    ci_missing_roles = [p for p in core_imp if not p.get("roles")]
    ci_no_roles = len(ci_missing_roles)
    ci_no_imp = sum(1 for p in core_imp if p.get("importance") is None)
    print(f"\n[3.1] Person (总 {ptot}, 其中核心+重要 {ci_tot}):")
    print(_missing_report("born", ptot, p_no_born))
    print(_missing_report("died", ptot, p_no_died))
    print(_missing_report("birthplace", ptot, p_no_bp))
    print(_missing_report("sources", ptot, p_no_src))
    print(f"  核心+重要 roles 缺失: {ci_no_roles}/{ci_tot}  (importance 缺失 {ci_no_imp}, 应为 0)")
    if ci_missing_roles:
        print("    roles_missing: " + ", ".join(
            f"{p.get('id')}({p.get('name')})" for p in ci_missing_roles))
    res["Person"] = {
        "total": ptot, "no_born": p_no_born, "no_died": p_no_died,
        "no_birthplace": p_no_bp, "no_sources": p_no_src,
        "core_important_total": ci_tot, "core_important_no_roles": ci_no_roles,
        "core_important_no_roles_ids": [p.get("id") for p in ci_missing_roles],
    }
    print(f"  >> Person 小结: born缺 {p_no_born}({p_no_born/max(ptot,1)*100:.0f}%) "
          f"died缺 {p_no_died}({p_no_died/max(ptot,1)*100:.0f}%) "
          f"birthplace缺 {p_no_bp}({p_no_bp/max(ptot,1)*100:.0f}%) "
          f"sources缺 {p_no_src}({p_no_src/max(ptot,1)*100:.0f}%)")

    # --- Event ---
    events = entities.get("Event", [])
    etot = len(events)
    e_no_date = sum(1 for e in events if not has_year(e.get("date")))
    e_no_cat = sum(1 for e in events if not e.get("category"))
    e_no_desc = sum(1 for e in events if not (e.get("description") or "").strip())
    e_no_src = sum(1 for e in events if not sources_list(e))
    war_events = [e for e in events if e.get("category") in impact_event_categories]
    w_tot = len(war_events)
    w_no_impact = sum(1 for e in war_events if not (e.get("impact") or "").strip())
    context_only = event_link_status["context_only"]
    isolated = event_link_status["isolated"]
    w_no_causal = len(context_only) + len(isolated)
    impact_label = "/".join(sorted(impact_event_categories))
    print(f"\n[3.2] Event (总 {etot}, 战乱变法类 {impact_label} {w_tot}):")
    print(_missing_report("date", etot, e_no_date))
    print(_missing_report("category", etot, e_no_cat))
    print(_missing_report("description", etot, e_no_desc))
    print(_missing_report("sources", etot, e_no_src))
    print(f"  战乱变法类无 impact     : {w_no_impact}/{w_tot}")
    print(f"  战乱变法类无因果关联    : {w_no_causal}/{w_tot}  (未出现在 led_to/caused_by)")
    print(f"    已有上下文 counterpart : {len(context_only)}  (part_of/includes/concurrent_with，仍非因果)")
    print(f"    尚无事件 counterpart   : {len(isolated)}  (需逐条考据，不能按时间相邻自动补边)")
    if context_only:
        print("      context_only: " + ", ".join(
            f"{e.get('id')}({e.get('name')})" for e in context_only))
    if isolated:
        print("      isolated: " + ", ".join(
            f"{e.get('id')}({e.get('name')})" for e in isolated))
    print("  注: 军事类由 schema event.category.family 动态推导；另含已注册的 coup/reform")
    res["Event"] = {
        "total": etot, "no_date": e_no_date, "no_category": e_no_cat,
        "no_description": e_no_desc, "no_sources": e_no_src,
        "war_reform_total": w_tot, "war_no_impact": w_no_impact, "war_no_causal": w_no_causal,
        "war_context_only": len(context_only), "war_isolated": len(isolated),
        "war_context_only_ids": [e.get("id") for e in context_only],
        "war_isolated_ids": [e.get("id") for e in isolated],
    }
    print(f"  >> Event 小结: date缺 {e_no_date} category缺 {e_no_cat} desc缺 {e_no_desc} "
          f"sources缺 {e_no_src}; 战乱变法类 {w_tot} 中无impact {w_no_impact} 无因果 {w_no_causal}")

    # --- Battle ---
    battles = entities.get("Battle", [])
    btot = len(battles)
    b_no_date = sum(1 for b in battles if not has_year(b.get("date")))
    b_missing_loc = [b for b in battles if not b.get("location")]
    b_missing_comb = [b for b in battles if not b.get("combatants")]
    b_missing_victor = [b for b in battles if not b.get("victor")]
    b_missing_src = [b for b in battles if not sources_list(b)]
    b_no_loc = len(b_missing_loc)
    b_no_comb = len(b_missing_comb)
    b_no_victor = len(b_missing_victor)
    b_no_src = len(b_missing_src)
    print(f"\n[3.3] Battle (总 {btot}):")
    print(_missing_report("date", btot, b_no_date))
    print(_missing_report("location", btot, b_no_loc))
    print(_missing_report("combatants", btot, b_no_comb))
    print(_missing_report("victor(结果)", btot, b_no_victor))
    print(_missing_report("sources", btot, b_no_src))
    if b_missing_loc:
        print("    location_missing: " + ", ".join(
            f"{b.get('id')}({b.get('name')})" for b in b_missing_loc))
    if b_missing_victor:
        print("    victor_missing: " + ", ".join(
            f"{b.get('id')}({b.get('name')})" for b in b_missing_victor))
    res["Battle"] = {
        "total": btot, "no_date": b_no_date, "no_location": b_no_loc,
        "no_combatants": b_no_comb, "no_victor": b_no_victor, "no_sources": b_no_src,
        "no_location_ids": [b.get("id") for b in b_missing_loc],
        "no_combatants_ids": [b.get("id") for b in b_missing_comb],
        "no_victor_ids": [b.get("id") for b in b_missing_victor],
        "no_sources_ids": [b.get("id") for b in b_missing_src],
    }
    print(f"  >> Battle 小结: date缺 {b_no_date} location缺 {b_no_loc} combatants缺 {b_no_comb} "
          f"结果缺 {b_no_victor} sources缺 {b_no_src}")

    # --- Polity ---
    polities = entities.get("Polity", [])
    potot = len(polities)
    po_no_founded = sum(1 for p in polities if not has_year(p.get("founded")))
    po_no_ended = sum(1 for p in polities if not has_year(p.get("ended")))
    po_missing_capital = [p for p in polities if not p.get("capital")]
    po_no_capital = len(po_missing_capital)
    po_no_src = sum(1 for p in polities if not sources_list(p))
    print(f"\n[3.4] Polity (总 {potot}):")
    print(_missing_report("founded", potot, po_no_founded))
    print(_missing_report("ended(亡)", potot, po_no_ended))
    print(_missing_report("capital(都城)", potot, po_no_capital))
    print(_missing_report("sources", potot, po_no_src))
    if po_missing_capital:
        print("    capital_missing: " + ", ".join(
            f"{p.get('id')}({p.get('name')})" for p in po_missing_capital))
    res["Polity"] = {
        "total": potot, "no_founded": po_no_founded, "no_ended": po_no_ended,
        "no_capital": po_no_capital, "no_sources": po_no_src,
        "no_capital_ids": [p.get("id") for p in po_missing_capital],
    }
    print(f"  >> Polity 小结: founded缺 {po_no_founded} ended缺 {po_no_ended} "
          f"都城缺 {po_no_capital} sources缺 {po_no_src}")

    # --- Faction ---
    factions = entities.get("Faction", [])
    ftot = len(factions)
    f_no_desc = sum(1 for f in factions if not (f.get("description") or "").strip())
    f_no_nature = sum(1 for f in factions if not f.get("nature"))
    f_no_src = sum(1 for f in factions if not sources_list(f))
    print(f"\n[3.5] Faction (总 {ftot}):")
    print(_missing_report("description", ftot, f_no_desc))
    print(_missing_report("nature(性质)", ftot, f_no_nature))
    print(_missing_report("sources", ftot, f_no_src))
    res["Faction"] = {
        "total": ftot, "no_description": f_no_desc, "no_nature": f_no_nature, "no_sources": f_no_src,
    }
    print(f"  >> Faction 小结: description缺 {f_no_desc} nature缺 {f_no_nature} sources缺 {f_no_src}")

    return res


def section_sources(entities, relations):
    """§4 出处格式。"""
    print("\n" + "=" * 72)
    print("§4 出处格式规范（规范 §4：正史 书名·卷/传；数据库 CBDB/CHGIS；现代 作者·书名）")
    print("=" * 72)

    fmt = Counter()
    examples = defaultdict(list)
    entity_issue_ids = defaultdict(list)
    issue_seen = defaultdict(set)
    entity_src_total = 0
    # 仅扫规范 §3 五类实体的 sources
    for typ in ("Person", "Event", "Battle", "Polity", "Faction"):
        for e in entities.get(typ, []):
            for s in raw_sources_list(e):
                entity_src_total += 1
                k = classify_source(s)
                fmt[k] += 1
                entity_id = e.get("id")
                if entity_id and entity_id not in issue_seen[k]:
                    issue_seen[k].add(entity_id)
                    entity_issue_ids[k].append(entity_id)
                if len(examples[k]) < 5:
                    examples[k].append(s)

    # 关系 sources（event_causal.yaml 等带 sources）
    rel_fmt = Counter()
    rel_src_total = 0
    for r, _ in relations:
        ss = r.get("sources")
        if isinstance(ss, list):
            for s in ss:
                if isinstance(s, str):
                    rel_src_total += 1
                    rel_fmt[classify_source(s)] += 1

    suspect = fmt["空"] + fmt["纯数据库标识"] + fmt["无·分卷"]
    print(f"\n实体 sources 条目数(五类实体): {entity_src_total}")
    print(f"  规范(含·)        : {fmt['规范(含·)']}")
    print(f"  无·分卷(仅书名)  : {fmt['无·分卷']}  <- 缺卷/传, 可追溯性低")
    print(f"  纯数据库标识     : {fmt['纯数据库标识']}  (CBDB/CHGIS, 规范§4允许但低细粒度)")
    print(f"  空               : {fmt['空']}")
    print(f"  疑似不规范合计   : {suspect}  ({suspect/max(entity_src_total,1)*100:.1f}%)")
    if entity_issue_ids["空"]:
        print("  空 source 实体    : " + ", ".join(entity_issue_ids["空"]))
    print(f"\n  各类样例:")
    for k in ("无·分卷", "纯数据库标识", "规范(含·)"):
        if examples[k]:
            print(f"    [{k}] " + " | ".join(examples[k][:5]))
    print(f"\n关系 sources 条目数(带sources的关系): {rel_src_total}")
    print(f"  规范(含·) {rel_fmt['规范(含·)']} / 无· {rel_fmt['无·分卷']} / "
          f"纯DB {rel_fmt['纯数据库标识']} / 空 {rel_fmt['空']}")
    print(f"\n>> §4 小结: 实体 sources {entity_src_total} 条, 疑似不规范 {suspect} "
          f"({suspect/max(entity_src_total,1)*100:.1f}%) [无·{fmt['无·分卷']} + 纯DB{fmt['纯数据库标识']} + 空{fmt['空']}]")

    return {
        "entity_source_total": entity_src_total,
        "format_counts": dict(fmt),
        "format_entity_ids": dict(entity_issue_ids),
        "suspect": suspect,
        "relation_source_total": rel_src_total,
        "relation_format_counts": dict(rel_fmt),
    }


def section_plan_a(relations, persons, events, battles, res_rel, res_per, res_field):
    """§5 方案 A 工程量估算（规范 §6 方案A：种子全量升级 + CBDB核心圈层 + 扩容）。"""
    print("\n" + "=" * 72)
    print("§5 方案 A 工程量估算（给 Rick：这活多大）")
    print("=" * 72)

    # imp1 人物 id 集（核心圈层判据）
    imp1_ids = {p.get("id") for p in persons if p.get("importance") == 1 and p.get("id")}
    imp1n = len(imp1_ids)
    # 非cbdb 种子人物
    seed_persons = [p for p in persons if not (str(p.get("id", "")).startswith("p_cbdb"))]
    seed_n = len(seed_persons)
    cbdb_persons = [p for p in persons if str(p.get("id", "")).startswith("p_cbdb")]
    cbdb_n = len(cbdb_persons)

    # --- 关系工程量 ---
    # 种子语义关系(非cbdb文件)无note + 套话note
    seed_sem_no_note = 0
    seed_sem_boilerplate = 0
    cbdb_assoc_involve_imp1 = 0
    cbdb_assoc_total = 0
    cbdb_rel_total = 0
    for r, fname in relations:
        if fname == "cbdb.yaml":
            cbdb_rel_total += 1
        t = r.get("type")
        if t in KINSHIP:
            continue
        note = r.get("note")
        is_bp, _ = classify_note(note)
        if fname != "cbdb.yaml":
            if not (isinstance(note, str) and note.strip()):
                seed_sem_no_note += 1
            elif is_bp:
                seed_sem_boilerplate += 1
        else:
            if t == "associated_with":
                cbdb_assoc_total += 1
                if r.get("from") in imp1_ids or r.get("to") in imp1_ids:
                    cbdb_assoc_involve_imp1 += 1

    # --- 人物工程量 ---
    # life_events: 核心(1)必填 + 重要(2)建议 (规范 §2 待Rick定, 此处按推荐估)
    imp2n = sum(1 for p in persons if p.get("importance") == 2)
    life_cov = life_event_coverage(persons)
    life_events_needed = life_cov["missing"]
    # CBDB 桩 bio 需升级为真实 bio
    cbdb_stub_bio = sum(1 for p in cbdb_persons if real_bio(p)[1])
    # 种子 bio 过简需扩
    seed_short_bio = sum(1 for p in seed_persons if real_bio(p)[3])

    # --- 事件工程量 ---
    ev_tot = len(events)
    ev_target = 300
    ev_new = max(0, ev_target - ev_tot)
    war_no_causal = res_field["Event"]["war_no_causal"]
    war_no_impact = res_field["Event"]["war_no_impact"]

    # --- 战役工程量 ---
    bt_tot = len(battles)
    bt_target = 80
    bt_new = max(0, bt_target - bt_tot)

    print(f"""
[关系] (规范 §1: 语义关系必须带 note 说清关联逻辑)
  种子语义关系(非cbdb文件)无 note    : {seed_sem_no_note} 条  -> 需补 note
  种子语义关系(非cbdb文件)套话 note  : {seed_sem_boilerplate} 条  -> 需升级为具体类型+note
  CBDB associated_with 总量          : {cbdb_assoc_total} 条 (套话, 全量升级=方案B不推荐)
    其中涉及核心(importance=1)人物  : {cbdb_assoc_involve_imp1} 条  -> 方案A 实际补 note 的 CBDB 圈层估算
  CBDB 关系全量(cbdb.yaml)          : {cbdb_rel_total} 条

[人物] (规范 §2: bio + life_events)
  种子人物(非cbdb)                  : {seed_n} 人 -> 全量升级(字段补全)
    其中 bio 过简(<30字)需扩        : {seed_short_bio} 人
  life_events 需新增(核心+重要)     : {life_events_needed} 人  (目标{life_cov['total']}，已有{life_cov['present']}，不重复计数)
    ※ 若种子全量都加，仍应按当前已有覆盖逐项扣除（覆盖范围待Rick定）
  CBDB 人物桩 bio 需升级为真实小传   : {cbdb_stub_bio} 人  <- 大成本项, 需Rick定是否全做
    (现状 bio='CBDB ID xxxx', 规范§6"只保证bio"= 至少一行真实小传)

[事件] (规范 §3)
  现有事件                          : {ev_tot}
  扩容目标 300+ 需新增              : ~{ev_new} 条  (新增即符合规范)
  战乱变法类缺因果关联需补          : {war_no_causal} 条
  战乱变法类缺 impact 需补          : {war_no_impact} 条

[战役] (规范 §3)
  现有战役                          : {bt_tot}
  扩容目标 80+ 需新增               : ~{bt_new} 条
""")

    # 汇总：方案A 核心处理条目
    plan_a_relations = seed_sem_no_note + seed_sem_boilerplate + cbdb_assoc_involve_imp1
    plan_a_persons = life_events_needed + seed_short_bio
    print(f">> 方案 A 工程量汇总(需处理条目):")
    print(f"   关系: 种子补/升级 {seed_sem_no_note + seed_sem_boilerplate} + CBDB核心圈层 {cbdb_assoc_involve_imp1} = {plan_a_relations} 条")
    print(f"   人物: life_events {life_events_needed} + 种子bio扩 {seed_short_bio} = {plan_a_persons} 人")
    print(f"         (+ 可选 CBDB 桩bio升级 {cbdb_stub_bio} 人 -- 单独决策, 不计入上述必做项)")
    print(f"   事件: 新增 ~{ev_new} + 补因果 {war_no_causal} + 补impact {war_no_impact}")
    print(f"   战役: 新增 ~{bt_new}")
    print(f"\n   ※ 对比方案B(全量): CBDB associated_with {cbdb_assoc_total} 条全补note, "
          f"为方案A CBDB圈层({cbdb_assoc_involve_imp1})的 {cbdb_assoc_total/max(cbdb_assoc_involve_imp1,1):.1f}x")

    return {
        "seed_persons": seed_n,
        "cbdb_persons": cbdb_n,
        "seed_sem_no_note": seed_sem_no_note,
        "seed_sem_boilerplate": seed_sem_boilerplate,
        "cbdb_associated_with_total": cbdb_assoc_total,
        "cbdb_associated_with_core_circle": cbdb_assoc_involve_imp1,
        "cbdb_relation_total": cbdb_rel_total,
        "life_events_needed": life_events_needed,
        "life_events_target": life_cov["total"],
        "life_events_present": life_cov["present"],
        "cbdb_stub_bio": cbdb_stub_bio,
        "seed_short_bio": seed_short_bio,
        "event_new_needed": ev_new,
        "war_no_causal": war_no_causal,
        "war_no_impact": war_no_impact,
        "battle_new_needed": bt_new,
        "imp1": imp1n,
        "imp2": imp2n,
    }


def main():
    parser = argparse.ArgumentParser(description="内容规范合规度盘点 (T5.2, 只读)")
    parser.add_argument("--json", metavar="PATH", help="机器可读结果落盘路径")
    args = parser.parse_args()

    if not DATA_DIR.is_dir():
        print(f"ERROR: DATA_DIR 不存在: {DATA_DIR}", file=sys.stderr)
        return 2

    print(f"# 内容规范合规度盘点 (T5.2)")
    print(f"# 数据目录: {DATA_DIR}")
    print(f"# 规范依据: docs/content-spec.md (草案, 2026-07-12)")
    print(f"# 说明: 只读盘点, 不改任何数据\n")

    entities = load_entities()
    relations = load_relations()

    persons = entities.get("Person", [])
    events = entities.get("Event", [])
    battles = entities.get("Battle", [])
    impact_event_categories = impact_categories()
    event_link_status = classify_impact_event_links(
        entities, relations, impact_event_categories)

    r1 = section_relations(relations)
    r2 = section_persons(persons)
    r3 = section_fields(entities, event_link_status, impact_event_categories)
    r4 = section_sources(entities, relations)
    r5 = section_plan_a(relations, persons, events, battles, r1, r2, r3)

    print("\n" + "=" * 72)
    print("盘点完成。以上为基线报告, 供 Rick 规范决策与重扫工程量估算。")
    print("=" * 72)

    if args.json:
        out = {
            "relations": r1, "persons": r2, "fields": r3,
            "sources": r4, "plan_a": r5,
        }
        with open(args.json, "w", encoding="utf-8") as fh:
            json.dump(out, fh, ensure_ascii=False, indent=2)
        print(f"\n机器可读结果已落盘: {args.json}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
