"""EdgeOne 发布 profile 的文件边界测试。"""
import json

import pytest

from scripts import build_edgeone


def test_safe_profile_excludes_restricted_map_sources():
    full_sources = build_edgeone.select_geojson_sources("full")
    safe_sources = build_edgeone.select_geojson_sources("safe")

    assert any(path.name.startswith("chgis_") for path in full_sources)
    assert safe_sources
    assert all(not path.name.startswith("chgis_") for path in safe_sources)
    assert len(safe_sources) < len(full_sources)


def test_frontend_profile_marker_must_match(monkeypatch, tmp_path):
    marker = tmp_path / "distribution-profile.json"
    marker.write_text(json.dumps({"distribution_profile": "safe"}), encoding="utf-8")
    monkeypatch.setattr(build_edgeone, "PROFILE", "full")

    with pytest.raises(RuntimeError, match="expected=full actual=safe"):
        build_edgeone.validate_frontend_profile(tmp_path)


def test_public_artifact_rejects_private_exploration_frontend(monkeypatch, tmp_path):
    marker = tmp_path / "distribution-profile.json"
    marker.write_text(json.dumps({
        "distribution_profile": "full",
        "private_explorations_enabled": True,
    }), encoding="utf-8")
    monkeypatch.setattr(build_edgeone, "PROFILE", "full")

    with pytest.raises(RuntimeError, match="private_explorations_enabled=false"):
        build_edgeone.validate_frontend_profile(tmp_path)


def test_public_artifact_accepts_demo_only_frontend(monkeypatch, tmp_path):
    marker = tmp_path / "distribution-profile.json"
    marker.write_text(json.dumps({
        "distribution_profile": "full",
        "private_explorations_enabled": False,
    }), encoding="utf-8")
    monkeypatch.setattr(build_edgeone, "PROFILE", "full")

    build_edgeone.validate_frontend_profile(tmp_path)
