"""内容审计工具的 schema 驱动口径测试。"""
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

import pytest
import yaml


ROOT = Path(__file__).resolve().parents[2]
SPEC = spec_from_file_location("audit_content", ROOT / "scripts/audit_content.py")
audit_content = module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(audit_content)


def _write_event_schema(tmp_path: Path, *, options, military):
    schema_dir = tmp_path / "schema"
    schema_dir.mkdir()
    (schema_dir / "event.yaml").write_text(
        yaml.safe_dump({
            "fields": {
                "category": {
                    "options": options,
                    "family": {"军事": military},
                },
            },
        }),
        encoding="utf-8",
    )
    return schema_dir


def test_impact_categories_follow_schema_military_family(tmp_path: Path):
    schema_dir = _write_event_schema(
        tmp_path,
        options=["battle", "war", "rebellion", "coup", "reform", "culture"],
        military=["battle", "war", "rebellion"],
    )

    assert audit_content.impact_categories(schema_dir) == {
        "battle", "war", "rebellion", "coup", "reform",
    }


def test_impact_categories_reject_unregistered_family_member(tmp_path: Path):
    schema_dir = _write_event_schema(
        tmp_path,
        options=["battle", "reform"],
        military=["battle", "war"],
    )

    with pytest.raises(ValueError, match="未注册项"):
        audit_content.impact_categories(schema_dir)


def test_impact_event_links_separate_causal_context_and_isolated():
    entities = {
        "Event": [
            {"id": "e_causal", "category": "war"},
            {"id": "e_context", "category": "battle"},
            {"id": "e_isolated", "category": "reform"},
            {"id": "e_counterpart", "category": "culture"},
        ],
        "Battle": [{"id": "b_context"}],
        "Person": [{"id": "p_actor"}],
        "Place": [{"id": "pl_scene"}],
    }
    relations = [
        ({"from": "e_causal", "to": "e_counterpart", "type": "led_to"}, "r.yaml"),
        # 同时有 context 边时 causal 必须优先，不能重复落进 context_only。
        ({"from": "e_causal", "to": "b_context", "type": "part_of"}, "r.yaml"),
        ({"from": "e_context", "to": "b_context", "type": "part_of"}, "r.yaml"),
        # 人物参与不是 Event/Battle counterpart，不能把因果缺口伪装成已建模。
        ({"from": "p_actor", "to": "e_isolated", "type": "participated_in"}, "r.yaml"),
        # 地点关系同样不算 counterpart。
        ({"from": "e_isolated", "to": "pl_scene", "type": "took_place_at"}, "r.yaml"),
    ]

    result = audit_content.classify_impact_event_links(
        entities, relations, {"war", "battle", "reform"})

    assert [event["id"] for event in result["causal"]] == ["e_causal"]
    assert [event["id"] for event in result["context_only"]] == ["e_context"]
    assert [event["id"] for event in result["isolated"]] == ["e_isolated"]


def test_life_event_coverage_subtracts_existing_work():
    people = [
        {"id": "core_done", "importance": 1, "life_events": [{"year": 1}]},
        {"id": "core_missing", "importance": 1},
        {"id": "important_empty", "importance": 2, "life_events": []},
        {"id": "general", "importance": 3},
    ]

    assert audit_content.life_event_coverage(people) == {
        "total": 3,
        "present": 1,
        "missing": 2,
        "missing_ids": ["core_missing", "important_empty"],
    }


def test_field_audit_includes_actionable_missing_entity_ids():
    entities = {
        "Person": [],
        "Event": [],
        "Battle": [
            {
                "id": "b_missing",
                "name": "待补战役",
                "type": "Battle",
                "date": {"year": 1},
                "combatants": ["k_a", "k_b"],
                "sources": ["史记·测试列传"],
            }
        ],
        "Polity": [
            {
                "id": "k_missing",
                "name": "待补政权",
                "type": "Polity",
                "founded": {"year": 1},
                "ended": {"year": 2},
                "sources": ["史记·测试世家"],
            }
        ],
        "Faction": [],
    }

    result = audit_content.section_fields(
        entities,
        {"context_only": [], "isolated": []},
        set(),
    )

    assert result["Battle"]["no_location_ids"] == ["b_missing"]
    assert result["Battle"]["no_victor_ids"] == ["b_missing"]
    assert result["Polity"]["no_capital_ids"] == ["k_missing"]


def test_source_audit_includes_actionable_entity_ids():
    entities = {
        "Person": [
            {"id": "p_blank", "sources": ["  "]},
            {"id": "p_book", "sources": ["史记"]},
            {"id": "p_db", "sources": ["CBDB (China Biographical Database)"]},
            {"id": "p_precise", "sources": ["史记·项羽本纪"]},
        ],
        "Event": [],
        "Battle": [],
        "Polity": [],
        "Faction": [],
    }

    result = audit_content.section_sources(entities, [])

    assert result["format_entity_ids"] == {
        "空": ["p_blank"],
        "无·分卷": ["p_book"],
        "纯数据库标识": ["p_db"],
        "规范(含·)": ["p_precise"],
    }
    assert audit_content.sources_list({"sources": ["", "  "]}) == []
