"""数据校验器内嵌引用与 march 合同测试。"""
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
import sys

import pytest


ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))
SPEC = spec_from_file_location("validate_data", SCRIPTS / "validate_data.py")
validate_data = module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(validate_data)


@pytest.fixture
def entities():
    return {
        "e_route": {"id": "e_route", "type": "Event"},
        "pl_start": {"id": "pl_start", "type": "Place"},
        "pl_end": {"id": "pl_end", "type": "Place"},
        "p_wrong": {"id": "p_wrong", "type": "Person"},
    }


def test_valid_march_collects_source_and_both_place_endpoints(entities):
    entity = {
        "id": "e_route",
        "type": "Event",
        "march": [{"from": "pl_start", "to": "pl_end"}],
    }

    endpoint_ids, issues = validate_data.validate_march(entity, entities)
    participants = validate_data.reference_participants(
        entity["id"], endpoint_ids)

    assert endpoint_ids == {"pl_start", "pl_end"}
    assert participants == {"e_route", "pl_start", "pl_end"}
    assert issues == []


def test_march_reports_dangling_endpoint_and_keeps_valid_endpoint(entities):
    entity = {
        "type": "Battle",
        "march": [{"from": "pl_missing", "to": "pl_end"}],
    }

    endpoint_ids, issues = validate_data.validate_march(entity, entities)

    assert endpoint_ids == {"pl_end"}
    assert [code for code, _ in issues] == ["E_DANGLING_REF"]
    assert "Battle.march[0].from" in issues[0][1]


def test_march_rejects_non_place_endpoint(entities):
    entity = {
        "type": "Event",
        "march": [{"from": "p_wrong", "to": "pl_end"}],
    }

    endpoint_ids, issues = validate_data.validate_march(entity, entities)

    assert endpoint_ids == {"pl_end"}
    assert [code for code, _ in issues] == ["E_REF_TYPE"]
    assert "必须为 Place" in issues[0][1]


@pytest.mark.parametrize(
    ("march", "message"),
    [
        ("pl_start -> pl_end", "march 必须为数组"),
        (["pl_start -> pl_end"], "march[0] 必须为映射"),
        ([{"from": "", "to": "pl_end"}], "march[0].from 必须为非空字符串"),
        ([{"from": "pl_start"}], "march[0].to 必须为非空字符串"),
    ],
)
def test_march_rejects_bad_structure(entities, march, message):
    endpoint_ids, issues = validate_data.validate_march(
        {"type": "Event", "march": march}, entities)

    assert issues
    assert all(code == "E_MARCH_STRUCTURE" for code, _ in issues)
    assert any(message in issue_message for _, issue_message in issues)
    if isinstance(march, list) and march and isinstance(march[0], dict):
        assert "pl_end" in endpoint_ids or "pl_start" in endpoint_ids
    else:
        assert endpoint_ids == set()


def test_valid_inline_reference_prevents_source_and_target_from_being_orphan(entities):
    entity = {
        "id": "e_route",
        "type": "Event",
        "location": "pl_start",
    }
    refs = {"location": ("Place", False)}

    inline_ids, issues = validate_data.validate_inline_references(
        entity, refs, entities)
    participants = validate_data.reference_participants(
        entity["id"], inline_ids)

    assert issues == []
    assert inline_ids == {"pl_start"}
    assert participants == {"e_route", "pl_start"}


def test_reference_owner_without_valid_target_remains_orphan(entities):
    inline_ids, inline_issues = validate_data.validate_inline_references(
        {"id": "e_route", "type": "Event", "location": "p_wrong"},
        {"location": ("Place", False)},
        entities,
    )
    march_ids, march_issues = validate_data.validate_march(
        {
            "id": "e_route",
            "type": "Event",
            "march": [{"from": "pl_missing", "to": "p_wrong"}],
        },
        entities,
    )

    assert inline_ids == set()
    assert march_ids == set()
    assert inline_issues and march_issues
    assert validate_data.reference_participants("e_route", inline_ids) == set()
    assert validate_data.reference_participants("e_route", march_ids) == set()
