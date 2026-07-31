import json
import re
from pathlib import Path


REPO = Path(__file__).resolve().parents[2]


def _integer(text: str, pattern: str) -> int:
    match = re.search(pattern, text)
    assert match, f"交接文档缺少可解析指标: {pattern!r}"
    return int(match.group(1).replace(",", ""))


def test_project_scale_matches_verified_validation_baseline():
    handoff = json.loads((REPO / "handoff.json").read_text(encoding="utf-8"))
    scale = handoff["project"]["scale"]
    baseline = handoff["verified_baselines"]["validate"]

    patterns = {
        "entities": r"entities\s*=\s*([\d,]+)",
        "relations": r"relations\s*=\s*([\d,]+)",
        "errors": r"errors\s*=\s*([\d,]+)",
        "warnings": r"warnings\s*=\s*([\d,]+)",
    }
    for label, pattern in patterns.items():
        assert _integer(scale, pattern) == _integer(baseline, pattern), label

    scale_orphans = _integer(scale, r"孤儿实体\s+([\d,]+)")
    baseline_orphans = _integer(baseline, r"孤儿实体\s+(?:[\d,]+→)?([\d,]+)")
    assert scale_orphans == baseline_orphans
