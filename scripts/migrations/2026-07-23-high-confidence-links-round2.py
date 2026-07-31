#!/usr/bin/env python3
"""补第二批本地证据闭合的实体引用与阶段行军路线。

本迁移只做逐键文本插入/替换，不用 ``yaml.dump`` 重写整份文件。所有目标在写入前
统一预检：实体 id 唯一、引用目标存在且类型正确、旧值符合预期、无已有冲突；第一次
运行应精确写入 3 个现代事件、60 个帝王归属、1 个巨鹿地点和 4 条阶段路线，第二次
运行必须是零改动 no-op。

幽州保卫战明确排除：正文的「易州」在河北，而现有 ``pl_yizhou`` 是益州/成都；
没有正确 Place 端点时宁可留空，不能借同音地名画箭头。
"""

from __future__ import annotations

import sys
from collections import defaultdict
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[2]
ENTITIES_DIR = ROOT / "data" / "entities"

MODERN_EVENTS = (
    "e_beijing_aoyun",
    "e_beijing_dongao",
    "e_shanghai_shibo",
)

# 目标 Polity -> (实体 ext.regime 的旧值, 人物 ids)。三个待合并重复实体刻意不在表中：
# p_tuoba_si / p_yelv_jing / p_yelv_zongzhen。
DYNASTY_GROUPS = {
    "k_dongwu": ("东吴", ("p_sun_hao", "p_sun_liang", "p_sun_xiu")),
    "k_dongjin": ("东晋", ("p_sima_dan",)),
    "k_donghan": (
        "东汉",
        (
            "p_liu_bian",
            "p_liu_bing",
            "p_liu_long",
            "p_liu_yi_shaodi",
            "p_liu_zhi_huandi",
            "p_liu_zuan",
        ),
    ),
    "k_dong_wei": ("东魏", ("p_yuan_shanjian",)),
    "k_yuan": ("元", ("p_asugiba", "p_haishan", "p_rinchinbal", "p_shidebala")),
    "k_liusong": (
        "刘宋",
        ("p_liu_jun", "p_liu_yifu", "p_liu_yu_houfeidi", "p_liu_zhun"),
    ),
    "k_bei_zhou": ("北周", ("p_yuwen_yu", "p_yuwen_yun")),
    "k_beiwei": (
        "北魏",
        (
            "p_tuoba_hong_xianwen",
            "p_tuoba_jun",
            "p_yuan_ke",
            "p_yuan_xiu",
            "p_yuan_xu",
            "p_yuan_ye",
            "p_yuan_ziyou",
        ),
    ),
    "k_bei_qi": ("北齐", ("p_gao_heng", "p_gao_zhan")),
    "k_nan_qi": (
        "南齐",
        ("p_xiao_baojuan", "p_xiao_baorong", "p_xiao_ze", "p_xiao_zhaoye"),
    ),
    "k_caowei": ("曹魏", ("p_cao_huan",)),
    "k_nan_liang": (
        "梁",
        ("p_xiao_dong", "p_xiao_fangzhi", "p_xiao_gang", "p_xiao_yi"),
    ),
    "k_xixia": (
        "西夏",
        (
            "p_li_bingchang",
            "p_li_chunyou",
            "p_li_dewang",
            "p_li_liangzuo",
            "p_li_qianshun",
            "p_li_renxiao",
            "p_li_xian_xixia",
            "p_li_zunxu",
        ),
    ),
    "k_xihan": ("西汉", ("p_liu_gong", "p_liu_hong_shaodi")),
    "k_xi_wei": ("西魏", ("p_yuan_kuo", "p_yuan_qin")),
    "k_liao": ("辽", ("p_yelv_hongji", "p_yelv_ruan", "p_yelv_yanxi")),
    "k_jin": (
        "金",
        (
            "p_wanyanwuqimai",
            "p_wanyan_dan",
            "p_wanyan_jing",
            "p_wanyan_xun",
            "p_wanyan_yongji",
        ),
    ),
    "k_nan_chen": ("陈", ("p_chen_bozong", "p_chen_qian")),
}

MARCHES = {
    "e_jian_guo_tang": {
        "from": "pl_taiyuan",
        "to": "pl_daxing",
        "note": (
            "617年李渊自太原起兵，进攻并攻克长安；此段只记晋阳起兵至入长安的"
            "建唐前置军事阶段，不把618年受禅建国概括成行军。《旧唐书·高祖本纪》"
            "《资治通鉴·卷185》"
        ),
        "sources": ["旧唐书·高祖本纪", "资治通鉴·卷185"],
    },
    "e_tang_shoufu_liangjing": {
        "from": "pl_daxing",
        "to": "pl_luoyang_sui",
        "note": (
            "757年九月唐军先收复长安，继而收复洛阳；此段只记收复两京的先后阶段，"
            "不延伸到河北追击。《旧唐书·肃宗本纪》《资治通鉴·卷220》"
        ),
        "sources": ["旧唐书·肃宗本纪", "资治通鉴·卷220"],
    },
    "b_gaolianghe": {
        "from": "pl_taiyuan",
        "to": "pl_youzhou",
        "note": (
            "宋太宗灭北汉后由太原径攻辽南京幽州；此段只记灭北汉后转攻幽州，"
            "不代替高梁河战场内的交战路线。《宋史·太宗本纪》《辽史·景宗本纪》"
        ),
        "sources": ["宋史·太宗本纪", "辽史·景宗本纪"],
    },
    "b_jiahe": {
        "from": "pl_yunzhou_lsd",
        "to": "pl_kaifeng",
        "note": (
            "923年李存勖从郓州突入，直捣汴梁灭后梁；此段只记夹河长期拉锯末期的"
            "郓州至汴梁进军，不概括917—923年全线。《资治通鉴·卷270-272》"
            "《新五代史·唐本纪》"
        ),
        "sources": ["资治通鉴·卷270-272", "新五代史·唐本纪"],
    },
}

EXPECTED_PENDING = {
    "modern_polities": len(MODERN_EVENTS),
    "dynasty_refs": sum(len(ids) for _regime, ids in DYNASTY_GROUPS.values()),
    "julu_location": 1,
    "marches": len(MARCHES),
}


def load_entities() -> tuple[dict[str, tuple[Path, dict]], list[str]]:
    """读取实体并返回唯一 id 索引；重复 id 单独返回，供写前拒绝执行。"""
    occurrences: dict[str, list[tuple[Path, dict]]] = defaultdict(list)
    for path in sorted(ENTITIES_DIR.glob("*/*.yaml")):
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        if isinstance(data, dict) and isinstance(data.get("id"), str):
            occurrences[data["id"]].append((path, data))
    duplicates = sorted(entity_id for entity_id, rows in occurrences.items() if len(rows) != 1)
    return {entity_id: rows[0] for entity_id, rows in occurrences.items() if len(rows) == 1}, duplicates


def require_entity(
    index: dict[str, tuple[Path, dict]],
    entity_id: str,
    entity_type: str,
    errors: list[str],
) -> tuple[Path, dict] | None:
    row = index.get(entity_id)
    if row is None:
        errors.append(f"实体不存在或 id 不唯一: {entity_id}")
        return None
    if row[1].get("type") != entity_type:
        errors.append(f"{entity_id} 类型为 {row[1].get('type')}，预期 {entity_type}")
        return None
    return row


def insert_before_key(text: str, key: str, block: str, entity_id: str) -> str:
    marker = f"{key}:"
    starts = [
        offset
        for offset in range(len(text))
        if text.startswith(marker, offset) and (offset == 0 or text[offset - 1] == "\n")
    ]
    if len(starts) != 1:
        raise ValueError(f"{entity_id}: 顶层键 {key} 出现 {len(starts)} 次，拒绝文本插入")
    offset = starts[0]
    return text[:offset] + block + text[offset:]


def main() -> int:
    index, duplicates = load_entities()
    errors: list[str] = []
    if duplicates:
        errors.append(f"存在重复实体 id: {duplicates}")

    pending: dict[str, int] = {key: 0 for key in EXPECTED_PENDING}
    replacements: dict[Path, str] = {}

    def current_text(path: Path) -> str:
        return replacements.get(path, path.read_text(encoding="utf-8"))

    def stage(path: Path, text: str) -> None:
        replacements[path] = text

    prc = require_entity(index, "k_prc", "Polity", errors)
    if prc:
        for entity_id in MODERN_EVENTS:
            row = require_entity(index, entity_id, "Event", errors)
            if row is None:
                continue
            path, entity = row
            value = entity.get("polities_involved")
            if value == ["k_prc"]:
                continue
            if value is not None:
                errors.append(f"{entity_id}: polities_involved 旧值冲突: {value!r}")
                continue
            if not isinstance(entity.get("sources"), list) or not entity["sources"]:
                errors.append(f"{entity_id}: 缺少既有 sources，拒绝补政权引用")
                continue
            try:
                text = insert_before_key(
                    current_text(path),
                    "description",
                    "polities_involved:\n- k_prc\n",
                    entity_id,
                )
            except ValueError as exc:
                errors.append(str(exc))
                continue
            stage(path, text)
            pending["modern_polities"] += 1

    seen_people: set[str] = set()
    for target_id, (expected_regime, person_ids) in DYNASTY_GROUPS.items():
        target = require_entity(index, target_id, "Polity", errors)
        if target is None:
            continue
        for person_id in person_ids:
            if person_id in seen_people:
                errors.append(f"人物被重复映射: {person_id}")
                continue
            seen_people.add(person_id)
            row = require_entity(index, person_id, "Person", errors)
            if row is None:
                continue
            path, person = row
            regime = (person.get("ext") or {}).get("regime")
            if regime != expected_regime:
                errors.append(
                    f"{person_id}: ext.regime={regime!r}，预期 {expected_regime!r}"
                )
            if not person.get("reign_start") or not person.get("reign_end"):
                errors.append(f"{person_id}: 缺 reign_start/reign_end，拒绝机械归属")
            if not isinstance(person.get("sources"), list) or not person["sources"]:
                errors.append(f"{person_id}: 缺 sources，拒绝机械归属")
            old = person.get("dynasty_ref")
            if old == target_id:
                continue
            if old is not None:
                errors.append(f"{person_id}: dynasty_ref 旧值冲突: {old!r}")
                continue
            try:
                text = insert_before_key(
                    current_text(path),
                    "bio",
                    f"dynasty_ref: {target_id}\n",
                    person_id,
                )
            except ValueError as exc:
                errors.append(str(exc))
                continue
            stage(path, text)
            pending["dynasty_refs"] += 1

    if len(seen_people) != EXPECTED_PENDING["dynasty_refs"]:
        errors.append(
            f"帝王映射数为 {len(seen_people)}，预期 {EXPECTED_PENDING['dynasty_refs']}"
        )

    julu_target = require_entity(index, "pl_julu_qi", "Place", errors)
    julu_old = require_entity(index, "pl_ju_lu_zhangjiao", "Place", errors)
    julu_event = require_entity(index, "e_julu_zhizhan", "Event", errors)
    if julu_target and "BC207 巨鹿之战" not in str(julu_target[1].get("description")):
        errors.append("pl_julu_qi: description 不再声明 BC207 巨鹿之战")
    if julu_old and "张角籍贯" not in str(julu_old[1].get("description")):
        errors.append("pl_ju_lu_zhangjiao: description 不再声明张角籍贯")
    if julu_event:
        path, event = julu_event
        old_location = event.get("location")
        if old_location == "pl_julu_qi":
            pass
        elif old_location == "pl_ju_lu_zhangjiao":
            old_line = "location: pl_ju_lu_zhangjiao"
            text = current_text(path)
            if text.count(old_line) != 1:
                errors.append("e_julu_zhizhan: 旧 location 文本不是唯一一行")
            else:
                stage(path, text.replace(old_line, "location: pl_julu_qi", 1))
                pending["julu_location"] += 1
        else:
            errors.append(f"e_julu_zhizhan: location 旧值冲突: {old_location!r}")

    # 易州/益州同音护栏：错误 Place 仍存在时，也必须证明没有被拿来画幽州援军路线。
    excluded = require_entity(index, "b_youzhou917", "Battle", errors)
    yizhou = require_entity(index, "pl_yizhou", "Place", errors)
    if excluded and "march" in excluded[1]:
        errors.append("b_youzhou917: 缺河北易州实体，必须保持无 march")
    if yizhou and (
        yizhou[1].get("name") != "益州" or yizhou[1].get("modern_name") != "成都"
    ):
        errors.append("pl_yizhou 语义已变化；需重新人工核对易州护栏")

    for entity_id, spec in MARCHES.items():
        row = index.get(entity_id)
        if row is None:
            errors.append(f"行军实体不存在或 id 不唯一: {entity_id}")
            continue
        path, entity = row
        if entity.get("type") not in {"Event", "Battle"}:
            errors.append(f"{entity_id}: march owner 类型错误 {entity.get('type')}")
            continue
        for endpoint in (spec["from"], spec["to"]):
            place = require_entity(index, endpoint, "Place", errors)
            if place and (
                place[1].get("latitude") is None or place[1].get("longitude") is None
            ):
                errors.append(f"{entity_id}: march 端点无坐标 {endpoint}")
        if entity.get("sources") != spec["sources"]:
            errors.append(
                f"{entity_id}: sources 已变化，预期 {spec['sources']!r}，"
                f"实得 {entity.get('sources')!r}"
            )
        expected_march = [
            {"from": spec["from"], "to": spec["to"], "note": spec["note"]}
        ]
        old_march = entity.get("march")
        if old_march == expected_march:
            continue
        if old_march is not None:
            errors.append(f"{entity_id}: 已有冲突 march: {old_march!r}")
            continue
        block = (
            "march:\n"
            f"- from: {spec['from']}\n"
            f"  to: {spec['to']}\n"
            f"  note: {spec['note']}\n"
        )
        try:
            text = insert_before_key(current_text(path), "location", block, entity_id)
        except ValueError as exc:
            errors.append(str(exc))
            continue
        stage(path, text)
        pending["marches"] += 1

    noop_run = all(value == 0 for value in pending.values())
    invalid_counts = {
        key: value
        for key, value in pending.items()
        if not 0 <= value <= EXPECTED_PENDING[key]
    }
    if invalid_counts:
        errors.append(
            f"候选数超出审计上限: {invalid_counts}，审计上限={EXPECTED_PENDING}"
        )

    if errors:
        print("拒绝执行：写入前预检失败", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1

    if noop_run:
        print(f"no-op: pending={pending}; changed_files=0")
        return 0

    for path, text in sorted(replacements.items()):
        path.write_text(text, encoding="utf-8")

    # 写后只读复验：每份改动仍须是可解析 YAML；字段值由同一预期再次核对。
    post_index, post_duplicates = load_entities()
    if post_duplicates:
        raise RuntimeError(f"写后出现重复 id: {post_duplicates}")
    for event_id in MODERN_EVENTS:
        if post_index[event_id][1].get("polities_involved") != ["k_prc"]:
            raise RuntimeError(f"写后复验失败: {event_id}.polities_involved")
    for target_id, (_regime, person_ids) in DYNASTY_GROUPS.items():
        for person_id in person_ids:
            if post_index[person_id][1].get("dynasty_ref") != target_id:
                raise RuntimeError(f"写后复验失败: {person_id}.dynasty_ref")
    if post_index["e_julu_zhizhan"][1].get("location") != "pl_julu_qi":
        raise RuntimeError("写后复验失败: e_julu_zhizhan.location")
    for entity_id, spec in MARCHES.items():
        expected = [{"from": spec["from"], "to": spec["to"], "note": spec["note"]}]
        if post_index[entity_id][1].get("march") != expected:
            raise RuntimeError(f"写后复验失败: {entity_id}.march")
    if "march" in post_index["b_youzhou917"][1]:
        raise RuntimeError("写后复验失败: b_youzhou917 不应出现 march")

    print(f"applied: pending={pending}; changed_files={len(replacements)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
