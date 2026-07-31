#!/usr/bin/env python3
"""数据校验器 (T1.2) —— 对 data/** 全量数据做结构与引用完整性校验。

一条命令产出：人类可读的分级报告（stdout）+ 机器可读结果（--json）+ 退出码
（存在 ERROR 退 1，否则退 0）。是后续所有数据批量任务（M4 重扫/扩容）的强制闸门。

校验规则分两级：
  ERROR（存在即退出码 1）
    - YAML 解析失败 / 缺 id / 缺 type / type 不在 schema 注册表
    - id 重复
    - 实体缺 schema 中 required:true 的字段（动态判定，不硬编码）
    - 关系两端 id 在实体集中不存在
    - 年份逻辑硬伤：born>died、founded>ended、关系 since>until、date>end_date
    - GeoJSON 坐标超出 WGS84 经度 [-180,180] / 纬度 [-90,90]
  WARN（计数与清单，不影响退出码）
    - 实体缺 sources 或为空（按类型统计缺失率）
    - 关系缺 note
    - 孤儿实体：不出现在任何关系两端、且正文不被任何其他实体双链提及
    - Person 无 born 或 died；Event 属 schema 军事族或 coup/reform 类却无 impact
    - GeoJSON 可解析、features 是否含 polity_id/polity_name（CHGIS 文件全缺作基线）
  内容规范合规 WARN (T5.1, 依据 docs/content-spec.md；默认不退出码)
    - §1 语义关系(非亲属)无 note / 模板套话 note（套话正则复用 audit_content.py）
    - §2 importance 1/2 人物缺 life_events；CBDB 桩 bio 单独计数
    - §3 战乱变法类(schema 军事族 + coup/reform) 既无 impact 又无因果关联
    - §4 sources 项无·且非纯DB标识(CBDB/CHGIS) -> 疑似不规范
  --strict-seed（重扫闸门）：种子文件(非 cbdb.yaml)语义关系无 note 升级为 ERROR(exit 1)

依赖：仅 pyyaml（已在 backend/requirements.txt）。不修改任何 data/ 文件。
"""
from __future__ import annotations

import argparse
import json
import math
import os
import re
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
# 支持 DATA_DIR / SCHEMA_DIR 环境变量（与 audit_content.py 对齐，便于 worktree/CI 切数据）；
# 不设时回退脚本所在仓库的 data/ schema/，行为与历史版本一致。
DATA_DIR = Path(os.environ.get("DATA_DIR", str(ROOT / "data")))
SCHEMA_DIR = Path(os.environ.get("SCHEMA_DIR", str(ROOT / "schema")))
ENTITIES_DIR = DATA_DIR / "entities"
RELATIONS_DIR = DATA_DIR / "relations"
GEO_DIR = DATA_DIR / "geo"

# 内容规范常量与套话判定：复用 audit_content.py（T5.2 只读盘点脚本）作为单一来源，
# 避免本文件与盘点脚本的套话正则分叉（任务书 T5.1 允许 import 复用）。
# audit_content.py 同目录，脚本运行时 sys.path[0] 含本目录，可直接 import。
import audit_content as _ac
KINSHIP_TYPES = _ac.KINSHIP                  # 亲属(自明)关系：豁免 note（规范 §1）
CAUSAL_TYPES = _ac.CAUSAL_TYPES              # 事件因果关联 led_to/caused_by
STUB_BIO_RE = _ac.STUB_BIO_RE                # CBDB 桩 bio: "CBDB ID xxxx"
classify_note = _ac.classify_note            # note -> (is_boilerplate, label)
classify_source = _ac.classify_source        # source -> '规范(含·)'/'纯数据库标识'/'无·分卷'/'空'

# 正文文本字段（与 backend/app/api/links.py TEXT_FIELDS 一致，保证双链语义对齐）
TEXT_FIELDS = ("bio", "description", "significance", "impact", "note", "pres_loc")

# Event 需校验 impact 的类别：与盘点脚本共享 schema 驱动口径，避免 schema 新增
# rebellion/conquest 后校验器仍只认识旧的三项。
EVENT_IMPACT_CATEGORIES = _ac.impact_categories(SCHEMA_DIR)
EVENT_IMPACT_LABEL = "/".join(sorted(EVENT_IMPACT_CATEGORIES))

# 名称索引的最短名称长度（与 links.py 一致：避免单字误匹配）
MIN_NAME_LEN = 2


def _has_cjk(s: str) -> bool:
    """是否含 CJK 统一表意文字（U+4E00..U+9FFF）。用于正文预筛。"""
    return any("一" <= ch <= "鿿" for ch in s)


# ---------------------------------------------------------------------------
# Schema
# ---------------------------------------------------------------------------

def load_schemas() -> dict[str, dict]:
    """加载 schema/*.yaml 中所有实体类型定义。

    判定标准：顶层含字符串型 `type` 与 `fields` 映射。据此天然排除
    relations.yaml（顶层是 `relations`）与非 yaml 文件。
    返回 {type_name: schema_dict}。
    """
    types: dict[str, dict] = {}
    for path in sorted(SCHEMA_DIR.glob("*.yaml")):
        try:
            with open(path, encoding="utf-8") as fh:
                sch = yaml.safe_load(fh)
        except Exception:
            continue
        if (isinstance(sch, dict)
                and isinstance(sch.get("type"), str)
                and isinstance(sch.get("fields"), dict)):
            types[sch["type"]] = sch
    return types


def required_fields(schema: dict) -> list[str]:
    """返回 schema 中标注 required:true 的字段名列表。"""
    out = []
    for fname, fdef in (schema.get("fields") or {}).items():
        if isinstance(fdef, dict) and fdef.get("required") is True:
            out.append(fname)
    return out


def ref_fields(schema: dict) -> dict[str, tuple[str, bool]]:
    """返回 schema 中的外键字段 -> (目标类型, 是否数组)。

    此前只有 relations/*.yaml 的两端被查，实体内嵌的外键（person.birthplace /
    polity.capital / event.polities_involved …）从没人查过 —— 于是 70 处引用指向
    不存在的 id、23 处指错实体类，而总览照报 errors=0。这是「静默丢弃」的同一类病：
    某个方向没人查，数据人间蒸发且不报错。
    """
    out: dict[str, tuple[str, bool]] = {}
    for fname, fdef in (schema.get("fields") or {}).items():
        if not isinstance(fdef, dict):
            continue
        if fdef.get("type") == "ref" and fdef.get("to"):
            out[fname] = (fdef["to"], False)
        elif fdef.get("type") == "array" and isinstance(fdef.get("items"), dict) \
                and fdef["items"].get("type") == "ref" and fdef["items"].get("to"):
            out[fname] = (fdef["items"]["to"], True)
    return out


def validate_inline_references(
        entity: dict,
        refs: dict[str, tuple[str, bool]],
        ent_by_id: dict[str, dict],
) -> tuple[set[str], list[tuple[str, str]]]:
    """校验实体顶层 schema 外键，返回（有效目标 id，错误 code/message）。

    只有存在且类型符合 schema ``to`` 的目标才算有效引用；调用方可把这些 id
    纳入孤儿判定。字段形状沿用既有容错口径，非字符串值由其它结构规则负责。
    """
    referenced_ids: set[str] = set()
    issues: list[tuple[str, str]] = []
    etype = entity.get("type")
    for field, (to_type, is_array) in refs.items():
        value = entity.get(field)
        if value is None:
            continue
        values = value if is_array and isinstance(value, list) else [value]
        for target_id in values:
            if not isinstance(target_id, str) or not target_id:
                continue
            target = ent_by_id.get(target_id)
            if target is None:
                issues.append((
                    "E_DANGLING_REF",
                    f"{etype}.{field} = '{target_id}' 不存在于实体集",
                ))
            elif target.get("type") != to_type:
                issues.append((
                    "E_REF_TYPE",
                    f"{etype}.{field} = '{target_id}' 是 {target.get('type')}，"
                    f"schema 声明 to: {to_type}",
                ))
            else:
                referenced_ids.add(target_id)
    return referenced_ids, issues


def validate_march(
        entity: dict,
        ent_by_id: dict[str, dict],
) -> tuple[set[str], list[tuple[str, str]]]:
    """校验 Event/Battle ``march`` 合同并返回有效 Place 端点。

    ``march`` 不在通用 schema ref_fields 中，因为它是对象数组；因此这里显式
    检查数组、leg 映射、from/to 非空字符串、目标存在且为 Place。
    """
    if "march" not in entity:
        return set(), []

    etype = entity.get("type")
    march = entity.get("march")
    if not isinstance(march, list):
        return set(), [(
            "E_MARCH_STRUCTURE",
            f"{etype}.march 必须为数组 (got {type(march).__name__})",
        )]

    endpoint_ids: set[str] = set()
    issues: list[tuple[str, str]] = []
    for index, leg in enumerate(march):
        if not isinstance(leg, dict):
            issues.append((
                "E_MARCH_STRUCTURE",
                f"{etype}.march[{index}] 必须为映射 (got {type(leg).__name__})",
            ))
            continue
        for side in ("from", "to"):
            target_id = leg.get(side)
            field = f"{etype}.march[{index}].{side}"
            if not isinstance(target_id, str) or not target_id.strip():
                issues.append((
                    "E_MARCH_STRUCTURE",
                    f"{field} 必须为非空字符串",
                ))
                continue
            target = ent_by_id.get(target_id)
            if target is None:
                issues.append((
                    "E_DANGLING_REF",
                    f"{field} = '{target_id}' 不存在于实体集",
                ))
            elif target.get("type") != "Place":
                issues.append((
                    "E_REF_TYPE",
                    f"{field} = '{target_id}' 是 {target.get('type')}，必须为 Place",
                ))
            else:
                endpoint_ids.add(target_id)
    return endpoint_ids, issues


def collect_non_orphan_ids(*reference_sets: set[str]) -> set[str]:
    """合并所有会让目标实体成为“被使用”的引用集合。"""
    non_orphan: set[str] = set()
    for ids in reference_sets:
        non_orphan.update(ids)
    return non_orphan


def reference_participants(owner_id: object, valid_target_ids: set[str]) -> set[str]:
    """有效结构化引用的参与者：owner 与至少一个有效目标共同计入。"""
    participants = set(valid_target_ids)
    if participants and isinstance(owner_id, str) and owner_id:
        participants.add(owner_id)
    return participants


# ---------------------------------------------------------------------------
# 年份比较工具（时代感知：数据中 BCE 年份混用两种写法）
#   - signed: 出现负年份 -> 遵循 schema「负=BCE」，数值已是天文学年，直接比较
#   - bce   : 正文含 "BC<数字>" 标记（手写实体如 "BC209"）-> 正数表示 BCE，
#             比较前取负换算成天文学年（月份不翻转），统一走数值大=晚
#   - ce    : 其余 -> 正数 CE，数值越大年代越晚
# ---------------------------------------------------------------------------

# 参与「时代判定」的年份字段
_ERA_YEAR_FIELDS = ("born", "died", "founded", "ended", "date", "end_date")
# 正文中 "BC<数字>" 形式的 BCE 标记（手写实体专用，CBDB 桩与 CE 实体均不含）
_BC_DIGIT_RE = re.compile(r"BC\d")
# 正文中 "AD<数字>" 形式的 CE 标记（用于识别横跨 BCE/CE 的实体，如王莽）
_AD_DIGIT_RE = re.compile(r"AD\d")


def ym_tuple(value) -> tuple[int, int | None] | None:
    """把 year_month 值规整为可比较的 (year, month|None)；不可解析返回 None。

    接受 {year, month?} 映射或裸 int。year 为负表示 BCE（int 比较天然正确）。
    """
    if value is None:
        return None
    if isinstance(value, bool):  # bool 是 int 子类，先排除
        return None
    if isinstance(value, int):
        return (value, None)
    if isinstance(value, dict):
        y = value.get("year")
        if isinstance(y, bool) or y is None:
            return None
        if not isinstance(y, int):
            try:
                y = int(y)
            except (TypeError, ValueError):
                return None
        m = value.get("month")
        if m is not None and not isinstance(m, int):
            try:
                m = int(m)
            except (TypeError, ValueError):
                m = None
        return (y, m)
    return None


def _raw_years(e: dict) -> list[int]:
    """收集实体年份字段中的裸 year 整数（用于判定是否含负年份=signed 约定）。"""
    yrs: list[int] = []
    for k in _ERA_YEAR_FIELDS:
        v = e.get(k)
        if isinstance(v, dict):
            y = v.get("year")
            if isinstance(y, int) and not isinstance(y, bool):
                yrs.append(y)
        elif isinstance(v, int) and not isinstance(v, bool):
            yrs.append(v)
    return yrs


def _has_bc_marker(e: dict) -> bool:
    """正文是否含 "BC<数字>" 形式 BCE 标记（手写 BCE 实体特征）。"""
    for k in TEXT_FIELDS:
        v = e.get(k)
        if isinstance(v, str) and _BC_DIGIT_RE.search(v):
            return True
    return False


def _entity_spans_bce_ce(e: dict) -> bool:
    """实体是否横跨 BCE/CE：正文同时含 "BC<数字>" 与 "AD<数字>" 标记。

    如王莽（BC1 任大司马、AD9 建新、AD23 卒）--born 在 BCE、died 在 CE。其 bce
    标签只代表「生平触及 BCE」，不能代表某条关系 since/until 的年代（该关系可能
    落在 CE）。故在关系 era 推断时须排除横跨实体，避免把 CE 关系误判成 BCE。
    """
    has_bc = has_ad = False
    for k in TEXT_FIELDS:
        v = e.get(k)
        if isinstance(v, str):
            if _BC_DIGIT_RE.search(v):
                has_bc = True
            if _AD_DIGIT_RE.search(v):
                has_ad = True
    return has_bc and has_ad


def detect_era(e: dict) -> str:
    """判定实体年份写法约定：'signed' / 'bce' / 'ce'。"""
    if any(y < 0 for y in _raw_years(e)):
        return "signed"
    if _has_bc_marker(e):
        return "bce"
    return "ce"


def detect_relation_era(r: dict, ent_by_id: dict[str, dict]) -> str:
    """判定关系 since/until 的年份写法约定：'signed' / 'bce' / 'ce'。

    判定来源（按优先级，era 只能来自记录本身或端点实体的「明确」年代信号）：
      1. since/until 含负年份 -> 'signed'（CBDB 约定，数值已是天文学年，直接比较）
      2. since/until 为正年份时看端点实体：仅当所有「非横跨」端点均为 bce/signed
         才判 'bce'（正数 BCE 年，year_hardship 内取负比较）；任一端点为 ce、或
         端点横跨 BCE/CE -> 'ce'。
    关键：横跨实体（如王莽，生平兼跨 BCE/CE）的 bce 标签不代表关系年代，须排除；
    且必须「所有」非横跨端点一致为 BCE 才判 bce，避免单个 BCE 端点把 CE 关系
    误拉成 BCE（王莽改革 9-22 是 CE，却被 p_wang_mang 的 BC 标记误判的根因）。
    """
    for key in ("since", "until"):
        v = r.get(key)
        if isinstance(v, dict):
            y = v.get("year")
            if isinstance(y, int) and not isinstance(y, bool) and y < 0:
                return "signed"
        elif isinstance(v, int) and not isinstance(v, bool) and v < 0:
            return "signed"
    endpoint_eras: list[str] = []
    for key in ("from", "to"):
        eid = r.get(key)
        if isinstance(eid, str) and eid in ent_by_id:
            e = ent_by_id[eid]
            if _entity_spans_bce_ce(e):
                continue  # 横跨实体不参与 bce 推断
            endpoint_eras.append(detect_era(e))
    if endpoint_eras and all(ea in ("bce", "signed") for ea in endpoint_eras):
        return "bce"
    return "ce"


def year_hardship(a, b, era: str) -> bool:
    """判断时间点 a 是否「晚于」b（对 start>end 即硬伤）。同年缺月不判定。

    统一换算成天文学年后按 (year, month) 元组比较，数值越大 = 时间越晚：
      signed/ce : 原值即天文学年（signed 已用负数表示 BCE，ce 为正数 CE）
      bce       : 正数表示 BCE，比较前取负（year_astro = -year），月份不参与
                  正负翻转。于是 -154 < -153（BC154 早于 BC153），同一 BCE 年内
                  月份大 = 时间晚（与 CE 一致，避免同年内月份比较被误反转）。
    """
    if a is None or b is None:
        return False
    ya, ma = a
    yb, mb = b
    if era == "bce":
        ya, yb = -ya, -yb
    if ya > yb:
        return True
    if ya < yb:
        return False
    if ma is None or mb is None:
        return False
    return ma > mb


# ---------------------------------------------------------------------------
# 加载
# ---------------------------------------------------------------------------

def load_entities():
    """遍历 data/entities/<*>/*.yaml，产出 (path, dict|None, error|None)。"""
    if not ENTITIES_DIR.is_dir():
        return
    for type_dir in sorted(ENTITIES_DIR.iterdir()):
        if not type_dir.is_dir():
            continue
        for fp in sorted(type_dir.glob("*.yaml")):
            try:
                with open(fp, encoding="utf-8") as fh:
                    data = yaml.safe_load(fh)
            except yaml.YAMLError as e:
                yield (fp, None, f"YAML 解析失败: {e}")
                continue
            except Exception as e:
                yield (fp, None, f"读取失败: {e}")
                continue
            if data is None:
                yield (fp, None, "空文件")
                continue
            if not isinstance(data, dict):
                yield (fp, None, f"顶层不是映射 (got {type(data).__name__})")
                continue
            yield (fp, data, None)


def load_relations():
    """遍历 data/relations/*.yaml，产出 (path, list|None, error|None)。"""
    if not RELATIONS_DIR.is_dir():
        return
    for fp in sorted(RELATIONS_DIR.glob("*.yaml")):
        try:
            with open(fp, encoding="utf-8") as fh:
                data = yaml.safe_load(fh)
        except yaml.YAMLError as e:
            yield (fp, None, f"YAML 解析失败: {e}")
            continue
        except Exception as e:
            yield (fp, None, f"读取失败: {e}")
            continue
        if data is None:
            yield (fp, [], None)  # 空文件视作 0 条关系
            continue
        if not isinstance(data, list):
            yield (fp, None, f"顶层不是列表 (got {type(data).__name__})")
            continue
        yield (fp, data, None)


def entity_text(e: dict) -> str:
    """拼接实体的正文文本字段（与 links.py TEXT_FIELDS 对齐）。"""
    parts = []
    for k in TEXT_FIELDS:
        v = e.get(k)
        if isinstance(v, str) and v:
            parts.append(v)
    return "\n".join(parts)


# ---------------------------------------------------------------------------
# 名称索引 + 双链扫描（复用 links.py NameIndex 思路，单遍扫描避免 O(N^2)）
# ---------------------------------------------------------------------------

def build_name_index(entities: list[dict]) -> dict[str, set[str]]:
    """建立 name->set(entity_id) 索引。收录 name/alias(aliases)/courtesy_name/
    art_name/modern_name，长度 >=2 的字符串。同名多实体（如 CBDB 重名）归并到同一 set。
    """
    name_to_ids: dict[str, set[str]] = defaultdict(set)
    for e in entities:
        eid = e.get("id")
        if not isinstance(eid, str):
            continue
        names: set[str] = set()
        n = e.get("name")
        if isinstance(n, str) and len(n) >= MIN_NAME_LEN:
            names.add(n)
        for key in ("alias", "aliases"):
            vals = e.get(key) or []
            if isinstance(vals, list):
                for v in vals:
                    if isinstance(v, str) and len(v) >= MIN_NAME_LEN:
                        names.add(v)
        for key in ("courtesy_name", "art_name"):
            v = e.get(key)
            if isinstance(v, str) and len(v) >= MIN_NAME_LEN:
                names.add(v)
        v = e.get("modern_name")
        if isinstance(v, str) and len(v) >= MIN_NAME_LEN:
            names.add(v)
        for nm in names:
            name_to_ids[nm].add(eid)
    return name_to_ids


def scan_mentions(entities: list[dict], name_to_ids: dict[str, set[str]]):
    """单遍扫描所有实体正文，返回:
      mentioned_ids  : 被任意「其他」实体正文提及的实体 id 集合（入链）
      outbound_ids   : 正文提及了任意其他实体的实体 id 集合（出链）

    对每个实体的文本，用 `name in text`（C 级子串查找）逐名探测；命中时把
    name 对应的实体 id（排除自身）记入 mentioned_ids。复杂度 O(E*N) 但子串
    查找走 C 层，7000 实体量级下数秒完成，与 links.py 同一量级。
    """
    mentioned_ids: set[str] = set()
    outbound_ids: set[str] = set()
    name_items = list(name_to_ids.items())  # 本地化，减少属性查找
    # 所有名称都是 CJK 时，无 CJK 的正文（如 CBDB 桩 "CBDB ID xxx"）可整段跳过
    all_names_cjk = all(_has_cjk(n) for n in name_to_ids) if name_to_ids else True
    for e in entities:
        eid = e.get("id")
        if not isinstance(eid, str):
            continue
        text = entity_text(e)
        if not text:
            continue
        if all_names_cjk and not _has_cjk(text):
            continue
        tlen = len(text)
        found_out = False
        for name, ids in name_items:
            if len(name) > tlen or name not in text:
                continue
            for x in ids:
                if x != eid:
                    mentioned_ids.add(x)
                    found_out = True
        if found_out:
            outbound_ids.add(eid)
    return mentioned_ids, outbound_ids


# ---------------------------------------------------------------------------
# GeoJSON
# ---------------------------------------------------------------------------

def _geojson_positions(obj):
    """递归产出 geometry 中的数值坐标对（含 GeometryCollection）。"""
    if isinstance(obj, dict):
        if "coordinates" in obj:
            yield from _geojson_positions(obj["coordinates"])
        for geometry in obj.get("geometries") or []:
            yield from _geojson_positions(geometry)
        return
    if not isinstance(obj, (list, tuple)):
        return
    if (len(obj) >= 2
            and isinstance(obj[0], (int, float)) and not isinstance(obj[0], bool)
            and isinstance(obj[1], (int, float)) and not isinstance(obj[1], bool)):
        yield obj[0], obj[1]
        return
    for child in obj:
        yield from _geojson_positions(child)


def check_geojson():
    """返回 (parse_errors, missing_ref_files, out_of_range_coordinates)。
    missing_ref = 至少没有一个 feature 的 properties 同时含 polity_id 与 polity_name。
    """
    parse_errors: list[tuple[str, str]] = []
    missing_ref: list[str] = []
    invalid_coords: list[tuple[str, str, float, float]] = []
    if not GEO_DIR.is_dir():
        return parse_errors, missing_ref, invalid_coords
    for fp in sorted(GEO_DIR.glob("*.geojson")):
        try:
            with open(fp, encoding="utf-8") as fh:
                gj = json.load(fh)
        except Exception as e:
            parse_errors.append((fp.name, str(e)))
            continue
        feats = gj.get("features") if isinstance(gj, dict) else None
        if not isinstance(feats, list) or not feats:
            missing_ref.append(fp.name)
            continue
        has_ref = False
        for index, ft in enumerate(feats):
            if not isinstance(ft, dict):
                continue
            props = ft.get("properties")
            feature_id = (ft.get("id")
                          or (props.get("sys_id") if isinstance(props, dict) else None)
                          or f"feature[{index}]")
            for lon, lat in _geojson_positions(ft.get("geometry") or {}):
                if (not math.isfinite(lon) or not math.isfinite(lat)
                        or not -180 <= lon <= 180 or not -90 <= lat <= 90):
                    # 每个 feature 报首个坏点，既能定位又避免一块投影错误刷数万条。
                    invalid_coords.append((fp.name, str(feature_id), lon, lat))
                    break
            if (isinstance(props, dict)
                    and "polity_id" in props and "polity_name" in props):
                has_ref = True
        if not has_ref:
            missing_ref.append(fp.name)
    return parse_errors, missing_ref, invalid_coords


# ---------------------------------------------------------------------------
# 主校验
# ---------------------------------------------------------------------------

def rel_path(fp: Path) -> str:
    """相对仓库根的路径，用于报告输出。"""
    try:
        return str(fp.relative_to(ROOT))
    except ValueError:
        return str(fp)


def run(strict_seed: bool = False):
    """运行校验。strict_seed=True 时把种子文件(非 cbdb.yaml)语义关系无 note
    升级为 ERROR（T5.3 重扫闸门）。"""
    t0 = time.perf_counter()
    schemas = load_schemas()
    req_by_type = {t: required_fields(s) for t, s in schemas.items()}
    ref_by_type = {t: ref_fields(s) for t, s in schemas.items()}

    # Person.roles 合法枚举（从 schema 读，schema 改则校验自动跟）
    _person_fields = (schemas.get("Person", {}).get("fields") or {})
    VALID_ROLES = set((((_person_fields.get("roles") or {}).get("items") or {})
                       .get("options")) or [])

    errors: list[dict] = []
    # WARN 各类别：存 (count, examples_list)
    warn = {
        "no_sources": {"count": 0, "by_type": Counter(), "total_by_type": Counter(), "examples": []},
        "rel_no_note": {"count": 0, "examples": []},
        "orphan": {"count": 0, "examples": []},
        "person_no_year": {"count": 0, "examples": []},
        "event_no_impact": {"count": 0, "examples": []},
        "geo_no_polity_ref": {"count": 0, "examples": []},
        "geo_parse_error": {"count": 0, "examples": []},
        "reign_bounds": {"count": 0, "examples": []},
        "person_roles": {"count": 0, "seed_total": 0, "with_roles": 0,
                         "role_counts": Counter(), "importance_dist": Counter()},
        # --- 内容规范合规 (T5.1, 依据 docs/content-spec.md) ---
        "spec_semantic": {"total": 0, "substantive": 0},       # §1 语义关系总数 / 实质 note 数
        "spec_rel_no_note": {"count": 0, "seed_count": 0, "examples": []},   # §1 语义关系无 note（含种子子计数）
        "spec_rel_boilerplate": {"count": 0, "examples": []},  # §1 语义关系套话 note
        "spec_person_no_life_events": {"count": 0, "imp12_total": 0, "examples": []},  # §2 imp1/2 缺 life_events
        "spec_stub_bio": {"count": 0, "examples": []},         # §2 CBDB 桩 bio
        "spec_event_no_causal_impact": {"count": 0, "total": 0, "examples": []},  # §3 coup/reform 无 impact 且无因果
        "spec_source_suspect": {"count": 0, "total": 0, "examples": []},  # §4 sources 无·且非纯DB
    }

    def add_error(code, fp, eid, msg):
        errors.append({"code": code, "file": rel_path(fp) if fp else None,
                       "id": eid, "message": msg})

    # ---- 加载实体（按 id 去重，构造唯一实体集）----
    ent_by_id: dict[str, dict] = {}
    id_first_seen: dict[str, Path] = {}
    entity_files = 0

    for fp, data, err in load_entities():
        entity_files += 1
        if err:
            add_error("E_PARSE", fp, None, err)
            continue
        eid = data.get("id")
        if not isinstance(eid, str) or not eid:
            add_error("E_NO_ID", fp, None, "缺少 id 字段或为空")
            continue
        if eid in ent_by_id:
            add_error("E_DUP_ID", fp, eid,
                      f"id 重复（首次见于 {rel_path(id_first_seen[eid])}）")
            continue
        id_first_seen[eid] = fp
        ent_by_id[eid] = data

    entities = list(ent_by_id.values())  # 唯一 id 实体集（WARN/扫描均基于此，避免重复计数）
    type_counts = Counter(e.get("type") or "<no-type>" for e in entities)
    inline_participant_ids: set[str] = set()
    march_participant_ids: set[str] = set()

    # ---- 实体结构校验 ----
    for e in entities:
        eid = e.get("id")
        fp = id_first_seen.get(eid)
        etype = e.get("type")
        if not isinstance(etype, str) or not etype:
            add_error("E_NO_TYPE", fp, eid, "缺少 type 字段")
            continue
        if etype not in schemas:
            add_error("E_UNKNOWN_TYPE", fp, eid,
                      f"type '{etype}' 不在 schema 注册表中（已注册: {sorted(schemas)}）")
            continue
        # required 字段
        for f in req_by_type[etype]:
            v = e.get(f)
            if v is None or (isinstance(v, str) and v == ""):
                add_error("E_MISSING_REQUIRED", fp, eid, f"缺少必填字段 '{f}'")
        # 内嵌外键：除校验存在性/类型外，也把有效目标纳入“被使用”集合。
        valid_refs, ref_issues = validate_inline_references(
            e, ref_by_type[etype], ent_by_id)
        inline_participant_ids.update(reference_participants(eid, valid_refs))
        for code, message in ref_issues:
            add_error(code, fp, eid, message)

        # march 是对象数组，无法由通用 ref_fields 表达；Event/Battle 显式硬校验。
        if etype in ("Event", "Battle"):
            valid_endpoints, march_issues = validate_march(e, ent_by_id)
            march_participant_ids.update(reference_participants(eid, valid_endpoints))
            for code, message in march_issues:
                add_error(code, fp, eid, message)
        # 年份硬伤（时代感知：signed/bce/ce 三种写法，覆盖
        # Person/Polity/Dynasty/Event/Battle）
        era = detect_era(e)
        born = ym_tuple(e.get("born"))
        died = ym_tuple(e.get("died"))
        if year_hardship(born, died, era):
            add_error("E_YEAR", fp, eid,
                      f"年份硬伤 born({e.get('born')}) > died({e.get('died')}) [{era}]")
        founded = ym_tuple(e.get("founded"))
        ended = ym_tuple(e.get("ended"))
        if year_hardship(founded, ended, era):
            add_error("E_YEAR", fp, eid,
                      f"年份硬伤 founded({e.get('founded')}) > ended({e.get('ended')}) [{era}]")
        date = ym_tuple(e.get("date"))
        end_date = ym_tuple(e.get("end_date"))
        if year_hardship(date, end_date, era):
            add_error("E_YEAR", fp, eid,
                      f"年份硬伤 date({e.get('date')}) > end_date({e.get('end_date')}) [{era}]")
        # roles/importance 越界校验（仅 Person；T4.0 身份/重要性地基）
        if etype == "Person":
            roles = e.get("roles")
            if roles is not None:
                if not isinstance(roles, list):
                    add_error("E_ROLE", fp, eid,
                              f"roles 必须为数组 (got {type(roles).__name__})")
                else:
                    for r in roles:
                        if r not in VALID_ROLES:
                            add_error("E_ROLE", fp, eid,
                                      f"roles 值 '{r}' 不在枚举内 (合法: {sorted(VALID_ROLES)})")
            imp = e.get("importance")
            if imp is not None:
                if isinstance(imp, bool) or not isinstance(imp, int) or not (1 <= imp <= 3):
                    add_error("E_IMPORTANCE", fp, eid,
                              f"importance 值 {imp!r} 不在 1-3")
            # reign 在位年起讫校验（T4.1b）：start≤end、end≤died、start≥born；越界=WARN。
            # era 复用实体 born/died/bio 判定（bce 正数取负 / signed 直接 / ce 直接），
            # reign 与 born/died 同约定写，故同一 era 下比较一致。
            rs = ym_tuple(e.get("reign_start"))
            re_ = ym_tuple(e.get("reign_end"))
            if rs is not None or re_ is not None:
                if (rs is not None and re_ is not None
                        and year_hardship(rs, re_, era)):
                    warn["reign_bounds"]["count"] += 1
                    if len(warn["reign_bounds"]["examples"]) < 20:
                        warn["reign_bounds"]["examples"].append(
                            f"{eid} 在位起讫倒置 reign_start({e.get('reign_start')}) "
                            f"> reign_end({e.get('reign_end')}) [{era}]")
                if (re_ is not None and died is not None
                        and year_hardship(re_, died, era)):
                    warn["reign_bounds"]["count"] += 1
                    if len(warn["reign_bounds"]["examples"]) < 20:
                        warn["reign_bounds"]["examples"].append(
                            f"{eid} 在位讫年晚于卒年 reign_end({e.get('reign_end')}) "
                            f"> died({e.get('died')}) [{era}]")
                if (rs is not None and born is not None
                        and year_hardship(born, rs, era)):
                    warn["reign_bounds"]["count"] += 1
                    if len(warn["reign_bounds"]["examples"]) < 20:
                        warn["reign_bounds"]["examples"].append(
                            f"{eid} 在位起年早于生年 reign_start({e.get('reign_start')}) "
                            f"< born({e.get('born')}) [{era}]")

    # ---- 加载关系 + 引用完整性 ----
    relations_total = 0
    relation_endpoint_ids: set[str] = set()
    causal_event_ids: set[str] = set()  # T5.1 §3：出现在 led_to/caused_by 的 event id
    for fp, data, err in load_relations():
        if err:
            add_error("E_PARSE", fp, None, err)
            continue
        for r in data:
            relations_total += 1
            if not isinstance(r, dict):
                continue
            frm = r.get("from")
            to = r.get("to")
            rtype = r.get("type")
            for side, val in (("from", frm), ("to", to)):
                if isinstance(val, str) and val:
                    relation_endpoint_ids.add(val)
                    if val not in ent_by_id:
                        add_error("E_DANGLING_REF", fp, None,
                                  f"关系端点 {side}={val} 不存在于实体集 "
                                  f"(type={rtype}, to={to if side=='from' else frm})")
                elif not isinstance(val, str) or not val:
                    # 缺 from/to：非任务规则，跳过（端点缺失不计入 endpoint 集）
                    pass
            # WARN: 关系缺 note
            note = r.get("note")
            if not (isinstance(note, str) and note.strip()):
                warn["rel_no_note"]["count"] += 1
                if len(warn["rel_no_note"]["examples"]) < 10:
                    warn["rel_no_note"]["examples"].append(
                        f"{frm} -[{rtype}]-> {to} [{rel_path(fp)}]")
            # 年份硬伤: since > until（时代感知）
            since = ym_tuple(r.get("since"))
            until = ym_tuple(r.get("until"))
            if since is not None and until is not None:
                rera = detect_relation_era(r, ent_by_id)
                if year_hardship(since, until, rera):
                    add_error("E_YEAR", fp, None,
                              f"关系 since({r.get('since')}) > until({r.get('until')}) "
                              f"[{rera}] {frm} -[{rtype}]-> {to}")

            # T5.1 §1 关系关联逻辑（规范核心：语义关系须 note 说清关联逻辑）
            # 亲属类型(father_of 等)自明豁免；其余=语义关系，无 note / 套话 note 均 WARN。
            is_seed_file = fp.name != "cbdb.yaml"
            if rtype not in KINSHIP_TYPES:
                warn["spec_semantic"]["total"] += 1
                rnote = r.get("note")
                has_note = isinstance(rnote, str) and rnote.strip()
                if not has_note:
                    warn["spec_rel_no_note"]["count"] += 1
                    if is_seed_file:
                        warn["spec_rel_no_note"]["seed_count"] += 1
                        # --strict-seed：种子语义关系无 note -> ERROR（T5.3 重扫闸门）
                        if strict_seed:
                            add_error("E_SEED_REL_NO_NOTE", fp, None,
                                      f"种子语义关系无 note: {frm} -[{rtype}]-> {to}")
                    if len(warn["spec_rel_no_note"]["examples"]) < 10:
                        tag = "种子" if is_seed_file else "cbdb"
                        warn["spec_rel_no_note"]["examples"].append(
                            f"{frm} -[{rtype}]-> {to} [{tag}] {rel_path(fp)}")
                else:
                    is_bp, lbl = classify_note(rnote)
                    if is_bp:
                        warn["spec_rel_boilerplate"]["count"] += 1
                        if len(warn["spec_rel_boilerplate"]["examples"]) < 10:
                            warn["spec_rel_boilerplate"]["examples"].append(
                                f"{frm} -[{rtype}]-> {to} [套话:{lbl}] {rel_path(fp)}")
                    else:
                        warn["spec_semantic"]["substantive"] += 1
            # T5.1 §3 因果关系端点累积（供 Event 检查：是否出现在 led_to/caused_by）
            if rtype in CAUSAL_TYPES:
                for val in (frm, to):
                    if isinstance(val, str) and val:
                        causal_event_ids.add(val)
            # T5.1 §4 关系 sources 出处格式（无·且非纯DB标识 -> 疑似不规范）
            rsrc = r.get("sources")
            if isinstance(rsrc, list):
                for s in rsrc:
                    warn["spec_source_suspect"]["total"] += 1
                    if isinstance(s, str) and classify_source(s) == "无·分卷":
                        warn["spec_source_suspect"]["count"] += 1
                        if len(warn["spec_source_suspect"]["examples"]) < 10:
                            warn["spec_source_suspect"]["examples"].append(s)

    # ---- WARN: 缺 sources ----
    for e in entities:
        eid = e.get("id")
        etype = e.get("type")
        if not isinstance(etype, str):
            continue
        warn["no_sources"]["total_by_type"][etype] += 1
        src = e.get("sources")
        if not (isinstance(src, list) and src):
            warn["no_sources"]["count"] += 1
            warn["no_sources"]["by_type"][etype] += 1
            if len(warn["no_sources"]["examples"]) < 10 and isinstance(eid, str):
                warn["no_sources"]["examples"].append(f"{eid} ({etype})")
        # T5.1 §4 出处格式：sources 项无·且非纯DB标识(CBDB/CHGIS) -> 疑似不规范
        if isinstance(src, list):
            for s in src:
                warn["spec_source_suspect"]["total"] += 1
                if isinstance(s, str) and classify_source(s) == "无·分卷":
                    warn["spec_source_suspect"]["count"] += 1
                    if len(warn["spec_source_suspect"]["examples"]) < 10:
                        warn["spec_source_suspect"]["examples"].append(s)

    # ---- WARN: Person 无 born 或 died ----
    for e in entities:
        if e.get("type") != "Person":
            continue
        eid = e.get("id")
        born = e.get("born")
        died = e.get("died")
        if born is None or died is None:
            warn["person_no_year"]["count"] += 1
            if len(warn["person_no_year"]["examples"]) < 10 and isinstance(eid, str):
                miss = []
                if born is None:
                    miss.append("born")
                if died is None:
                    miss.append("died")
                warn["person_no_year"]["examples"].append(
                    f"{eid} (缺 {'/'.join(miss)})")
        # T5.1 §2 人物生平：importance 1/2(核心+重要) 须 life_events
        imp = e.get("importance")
        if isinstance(imp, int) and not isinstance(imp, bool) and imp in (1, 2):
            warn["spec_person_no_life_events"]["imp12_total"] += 1
            if not e.get("life_events"):
                warn["spec_person_no_life_events"]["count"] += 1
                if len(warn["spec_person_no_life_events"]["examples"]) < 10 and isinstance(eid, str):
                    warn["spec_person_no_life_events"]["examples"].append(
                        f"{eid} (importance={imp})")
        # T5.1 §2 CBDB 桩 bio 单独计数（bio='CBDB ID xxxx'，非真实小传）
        bio = e.get("bio")
        if isinstance(bio, str) and STUB_BIO_RE.match(bio):
            warn["spec_stub_bio"]["count"] += 1
            if len(warn["spec_stub_bio"]["examples"]) < 10 and isinstance(eid, str):
                warn["spec_stub_bio"]["examples"].append(eid)
        # 身份/重要性标注统计（仅种子人物=非 cbdb；T4.0）
        if isinstance(eid, str) and not eid.startswith("p_cbdb_"):
            warn["person_roles"]["seed_total"] += 1
            roles = e.get("roles")
            if isinstance(roles, list) and roles:
                warn["person_roles"]["with_roles"] += 1
                for r in roles:
                    warn["person_roles"]["role_counts"][r] += 1
            imp = e.get("importance")
            if isinstance(imp, int) and not isinstance(imp, bool):
                warn["person_roles"]["importance_dist"][imp] += 1

    # ---- WARN: Event(schema 军事族 + coup/reform) 无 impact ----
    for e in entities:
        if e.get("type") != "Event":
            continue
        cat = e.get("category")
        if cat not in EVENT_IMPACT_CATEGORIES:
            continue
        impact = e.get("impact")
        eid = e.get("id")
        # T5.1 §3 战乱变法类(coup/reform) 须 impact + 因果关联，两者皆无 -> WARN
        if cat in EVENT_IMPACT_CATEGORIES:
            warn["spec_event_no_causal_impact"]["total"] += 1
            has_impact = isinstance(impact, str) and impact.strip()
            in_causal = isinstance(eid, str) and eid in causal_event_ids
            if not has_impact and not in_causal:
                warn["spec_event_no_causal_impact"]["count"] += 1
                if len(warn["spec_event_no_causal_impact"]["examples"]) < 10 and isinstance(eid, str):
                    warn["spec_event_no_causal_impact"]["examples"].append(
                        f"{eid} (category={cat}, 无impact且无因果关联)")
        if not (isinstance(impact, str) and impact.strip()):
            warn["event_no_impact"]["count"] += 1
            if len(warn["event_no_impact"]["examples"]) < 10 and isinstance(eid, str):
                warn["event_no_impact"]["examples"].append(
                    f"{eid} (category={cat})")

    # ---- 双链扫描 + 孤儿实体 ----
    name_to_ids = build_name_index(entities)
    mentioned_ids, outbound_ids = scan_mentions(entities, name_to_ids)
    non_orphan = collect_non_orphan_ids(
        relation_endpoint_ids,
        mentioned_ids,
        inline_participant_ids,
        march_participant_ids,
    )
    for e in entities:
        eid = e.get("id")
        if not isinstance(eid, str):
            continue
        if eid not in non_orphan:
            warn["orphan"]["count"] += 1
            if len(warn["orphan"]["examples"]) < 10:
                warn["orphan"]["examples"].append(
                    f"{eid} [{e.get('type')}] {e.get('name') or ''}")

    # ---- GeoJSON ----
    geo_parse, geo_missing, geo_invalid = check_geojson()
    geo_total = len(list(GEO_DIR.glob("*.geojson"))) if GEO_DIR.is_dir() else 0
    warn["geo_parse_error"]["count"] = len(geo_parse)
    warn["geo_parse_error"]["examples"] = [f"{n}: {m}" for n, m in geo_parse[:10]]
    warn["geo_no_polity_ref"]["count"] = len(geo_missing)
    warn["geo_no_polity_ref"]["examples"] = geo_missing[:10]
    for filename, feature_id, lon, lat in geo_invalid:
        add_error(
            "E_GEOJSON_COORD_RANGE",
            GEO_DIR / filename,
            feature_id,
            f"坐标超出 WGS84 范围: lon={lon}, lat={lat}",
        )

    elapsed = time.perf_counter() - t0

    # ---- 汇总 ----
    total_entities = len(entities)
    # spec_semantic 仅作基数(total/substantive)无 count -> .get 跳过；其余 spec 项 count 计入
    total_warnings = sum(v.get("count", 0) for v in warn.values())
    inbound = len(mentioned_ids & ent_by_id.keys())
    outbound = len(outbound_ids & ent_by_id.keys())
    coverage = (inbound / len(ent_by_id)) if ent_by_id else 0.0

    report = {
        "summary": {
            "entity_files": entity_files,
            "entities": total_entities,
            "relations": relations_total,
            "errors": len(errors),
            "warnings": total_warnings,
            "elapsed_sec": round(elapsed, 2),
        },
        "registered_types": sorted(schemas),
        "type_counts": dict(type_counts),
        "geojson_files": geo_total,
        "wiki_link": {
            "entities_total": len(ent_by_id),
            "entities_with_inbound": inbound,
            "entities_with_outbound": outbound,
            "coverage": round(coverage, 4),
            "orphan_count": warn["orphan"]["count"],
        },
        "errors": errors,
        "warnings": {
            "no_sources": {
                "count": warn["no_sources"]["count"],
                "by_type": {
                    t: {"missing": warn["no_sources"]["by_type"].get(t, 0),
                        "total": warn["no_sources"]["total_by_type"].get(t, 0)}
                    for t in sorted(warn["no_sources"]["total_by_type"])
                },
                "examples": warn["no_sources"]["examples"],
            },
            "relation_missing_note": {
                "count": warn["rel_no_note"]["count"],
                "examples": warn["rel_no_note"]["examples"],
            },
            "orphan_entities": {
                "count": warn["orphan"]["count"],
                "examples": warn["orphan"]["examples"],
            },
            "person_missing_born_died": {
                "count": warn["person_no_year"]["count"],
                "examples": warn["person_no_year"]["examples"],
            },
            "event_missing_impact": {
                "count": warn["event_no_impact"]["count"],
                "examples": warn["event_no_impact"]["examples"],
            },
            "geojson_missing_polity_ref": {
                "count": warn["geo_no_polity_ref"]["count"],
                "files": warn["geo_no_polity_ref"]["examples"],
            },
            "geojson_parse_error": {
                "count": warn["geo_parse_error"]["count"],
                "files": warn["geo_parse_error"]["examples"],
            },
            "reign_bounds": {
                "count": warn["reign_bounds"]["count"],
                "examples": warn["reign_bounds"]["examples"],
            },
            "person_roles": {
                "seed_total": warn["person_roles"]["seed_total"],
                "with_roles": warn["person_roles"]["with_roles"],
                "roles_coverage": round(
                    warn["person_roles"]["with_roles"]
                    / max(1, warn["person_roles"]["seed_total"]), 4),
                "role_counts": dict(warn["person_roles"]["role_counts"]),
                "importance_dist": dict(warn["person_roles"]["importance_dist"]),
            },
        },
    }
    # ---- 内容规范合规汇总 (T5.1, 依据 docs/content-spec.md) ----
    sem_total = warn["spec_semantic"]["total"]
    sem_sub = warn["spec_semantic"]["substantive"]
    imp12_total = warn["spec_person_no_life_events"]["imp12_total"]
    imp12_miss = warn["spec_person_no_life_events"]["count"]
    ev_total = warn["spec_event_no_causal_impact"]["total"]
    ev_bad = warn["spec_event_no_causal_impact"]["count"]
    src_total = warn["spec_source_suspect"]["total"]
    src_bad = warn["spec_source_suspect"]["count"]
    seed_no_note_errors = sum(1 for e in errors if e["code"] == "E_SEED_REL_NO_NOTE")
    report["content_spec"] = {
        "strict_seed": strict_seed,
        "seed_rel_no_note_errors": seed_no_note_errors,
        "relation_logic": {
            "semantic_total": sem_total,
            "no_note": warn["spec_rel_no_note"]["count"],
            "no_note_seed": warn["spec_rel_no_note"]["seed_count"],
            "boilerplate": warn["spec_rel_boilerplate"]["count"],
            "substantive": sem_sub,
            "compliance_rate": round(sem_sub / max(sem_total, 1), 4),
            "examples_no_note": warn["spec_rel_no_note"]["examples"],
            "examples_boilerplate": warn["spec_rel_boilerplate"]["examples"],
        },
        "person_life": {
            "imp12_total": imp12_total,
            "missing_life_events": imp12_miss,
            "life_events_compliance": round((imp12_total - imp12_miss) / max(imp12_total, 1), 4),
            "stub_bio": warn["spec_stub_bio"]["count"],
            "examples": warn["spec_person_no_life_events"]["examples"],
        },
        "event_causal": {
            "reform_total": ev_total,
            "no_impact_no_causal": ev_bad,
            "compliance_rate": round((ev_total - ev_bad) / max(ev_total, 1), 4),
            "examples": warn["spec_event_no_causal_impact"]["examples"],
        },
        "source_format": {
            "total": src_total,
            "suspect": src_bad,
            "compliance_rate": round((src_total - src_bad) / max(src_total, 1), 4),
            "examples": warn["spec_source_suspect"]["examples"],
        },
    }

    return report, errors, warn, elapsed, entity_files, total_entities, \
        relations_total, total_warnings, inbound, outbound, coverage, geo_total


def print_report(report, errors, warn, elapsed, entity_files, total_entities,
                 relations_total, total_warnings, inbound, outbound, coverage,
                 geo_total):
    schemas = report["registered_types"]
    type_counts = report["type_counts"]
    ent_by_id_count = report["wiki_link"]["entities_total"]

    print("=" * 60)
    print("数据校验报告 (validate_data.py)")
    print("=" * 60)
    print(f"schema 注册类型: {', '.join(schemas)}")
    print(f"实体文件: {entity_files}（唯一 id 实体: {total_entities}）  "
          f"关系条目: {relations_total}  geojson: {geo_total}")
    print(f"实体类型分布: {dict(type_counts)}")
    print()

    # ERROR
    print(f"--- ERROR ({len(errors)} 条) ---")
    if not errors:
        print("（无）")
    else:
        for e in errors:
            loc = e["file"] or "?"
            eid = f" {e['id']}" if e.get("id") else ""
            print(f"[ERROR] {loc}{eid}  {e['code']}: {e['message']}")
    print()

    # WARN
    print("--- WARN ---")
    # 缺 sources
    w = warn["no_sources"]
    by_type_str = ", ".join(
        f"{t}: {report['warnings']['no_sources']['by_type'][t]['missing']}/"
        f"{report['warnings']['no_sources']['by_type'][t]['total']}"
        f" ({round(100 * report['warnings']['no_sources']['by_type'][t]['missing'] / max(1, report['warnings']['no_sources']['by_type'][t]['total']))}%)"
        for t in sorted(report['warnings']['no_sources']['by_type']))
    print(f"[缺 sources] {w['count']} 例 (按类型缺失率: {by_type_str})")
    _print_examples(w["examples"])
    print()

    w = warn["rel_no_note"]
    print(f"[关系缺 note] {w['count']} 例")
    _print_examples(w["examples"])
    print()


    w = warn["orphan"]
    print(f"[孤儿实体] {w['count']} 例")
    _print_examples(w["examples"])
    print()

    w = warn["person_no_year"]
    print(f"[Person 无 born/died] {w['count']} 例")
    _print_examples(w["examples"])
    print()

    w = warn["event_no_impact"]
    print(f"[Event({EVENT_IMPACT_LABEL}) 无 impact] {w['count']} 例")
    _print_examples(w["examples"])
    print()

    w = warn["geo_no_polity_ref"]
    print(f"[GeoJSON 缺 polity_id/polity_name] {w['count']} 文件（CHGIS 文件全缺为基线）")
    _print_examples(w["examples"])
    print()

    w = warn["geo_parse_error"]
    print(f"[GeoJSON 解析失败] {w['count']} 文件")
    _print_examples(w["examples"])
    print()

    # 帝王在位年越界（T4.1b）
    w = warn["reign_bounds"]
    print(f"[帝王在位年越界] {w['count']} 例 (规则: reign_start≤reign_end、reign_end≤died、reign_start≥born)")
    _print_examples(w["examples"])
    print()

    # 人物身份/重要性标注（T4.0）
    w = warn["person_roles"]
    seed_total = w["seed_total"]
    with_roles = w["with_roles"]
    cov = round(100 * with_roles / max(1, seed_total), 1)
    print(f"[人物身份/重要性] 种子人物 {with_roles}/{seed_total} 有 roles 标注 ({cov}%)")
    role_str = ", ".join(f"{r}: {c}" for r, c in sorted(w["role_counts"].items(), key=lambda x: -x[1]))
    print(f"  roles 计数: {role_str or '(无)'}")
    imp_label = {1: "核心", 2: "重要", 3: "一般"}
    imp_str = ", ".join(f"{k}({imp_label.get(k, '?')}): {v}"
                        for k, v in sorted(w["importance_dist"].items()))
    print(f"  importance 分布: {imp_str or '(无)'}")
    print()

    # 双链覆盖
    print("--- 双链覆盖 ---")
    print(f"被正文提及实体(入链): {inbound} / {ent_by_id_count} "
          f"({round(100 * coverage, 1)}%)")
    print(f"有出链实体: {outbound} / {ent_by_id_count} "
          f"({round(100 * outbound / max(1, ent_by_id_count), 1)}%)")
    print()

    # 内容规范合规 (T5.1)
    cs = report.get("content_spec") or {}
    if cs:
        print("--- 内容规范合规 (T5.1, 依据 docs/content-spec.md) ---")
        rl = cs["relation_logic"]
        print(f"[关系关联逻辑 §1] 语义关系 {rl['semantic_total']} 条 (亲属豁免不计)")
        print(f"  无 note       : {rl['no_note']} 例 (其中种子文件 {rl['no_note_seed']} 例 <- --strict-seed 闸门)")
        print(f"  套话 note     : {rl['boilerplate']} 例")
        print(f"  实质 note     : {rl['substantive']} 例")
        print(f"  合规率(实质/语义): {round(100 * rl['compliance_rate'], 1)}%")
        _print_examples(rl["examples_no_note"])
        print()

        pl = cs["person_life"]
        print(f"[人物生平 §2] 核心+重要(importance 1/2) {pl['imp12_total']} 人")
        print(f"  缺 life_events : {pl['missing_life_events']} 例 (合规率 {round(100 * pl['life_events_compliance'], 1)}%)")
        print(f"  CBDB 桩 bio    : {pl['stub_bio']} 例 (bio='CBDB ID xxxx', 非真实小传)")
        _print_examples(pl["examples"])
        print()

        ev = cs["event_causal"]
        print(f"[事件因果 §3] 战乱变法类(coup/reform) {ev['reform_total']} 条")
        print(f"  既无 impact 又无因果关联 : {ev['no_impact_no_causal']} 例 (合规率 {round(100 * ev['compliance_rate'], 1)}%)")
        _print_examples(ev["examples"])
        print()

        sf = cs["source_format"]
        print(f"[出处格式 §4] sources 项 {sf['total']} 条")
        print(f"  疑似不规范(无·且非纯DB) : {sf['suspect']} 例 (合规率 {round(100 * sf['compliance_rate'], 1)}%)")
        _print_examples(sf["examples"])
        print()

        mode = "on" if cs["strict_seed"] else "off"
        print(f"[严格模式] --strict-seed={mode}; 种子语义关系无note ERROR: "
              f"{cs['seed_rel_no_note_errors']} 条")
        print()

    print(f"总览: entities={total_entities} relations={relations_total} "
          f"errors={len(errors)} warnings={total_warnings}  耗时 {round(elapsed, 2)}s")


def _print_examples(examples):
    for ex in examples[:10]:
        print(f"    - {ex}")
    if len(examples) > 10:
        print(f"    ... 共 {len(examples)}+ (见 --json)")


def main():
    parser = argparse.ArgumentParser(description="data/** 数据结构与引用完整性校验")
    parser.add_argument("--json", metavar="PATH", help="完整机器可读结果落盘路径")
    parser.add_argument("--strict-seed", action="store_true",
                        help="严格模式(重扫闸门): 种子文件(非 cbdb.yaml)语义关系无 note "
                             "升级为 ERROR(exit 1)。T5.3 补完种子 note 后应归 0。")
    args = parser.parse_args()

    (report, errors, warn, elapsed, entity_files, total_entities,
     relations_total, total_warnings, inbound, outbound, coverage,
     geo_total) = run(strict_seed=args.strict_seed)

    print_report(report, errors, warn, elapsed, entity_files, total_entities,
                 relations_total, total_warnings, inbound, outbound, coverage,
                 geo_total)

    if args.json:
        out = Path(args.json)
        out.parent.mkdir(parents=True, exist_ok=True)
        with open(out, "w", encoding="utf-8") as fh:
            json.dump(report, fh, ensure_ascii=False, indent=2)
        print(f"\n[json 已落盘] {out}")

    sys.exit(1 if errors else 0)


if __name__ == "__main__":
    main()
