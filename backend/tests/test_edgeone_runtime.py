"""EdgeOne 紧凑运行包的回归测试。"""
import json
from pathlib import Path

from app.core import data
from app.main import APP_VERSION, create_app


def _write_json(path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")


def test_api_version_matches_release_package():
    package = json.loads(
        (Path(__file__).resolve().parents[2] / "package.json").read_text(encoding="utf-8")
    )
    assert APP_VERSION == package["version"]


def test_compiled_runtime_data_takes_precedence(monkeypatch, tmp_path):
    """云函数只携带编译 JSON 时，不应回退到 YAML 真相源。"""
    compiled = tmp_path / "_compiled"
    entities = [{"id": "p_test", "type": "Person", "name": "测试人物"}]
    relations = [{"from": "p_test", "to": "pl_test", "type": "visited"}]
    registry = {"Person": {"type": "Person"}}
    relation_schema = [{"type": "visited"}]

    _write_json(compiled / "entities.json", entities)
    _write_json(compiled / "relations.json", relations)
    _write_json(compiled / "schema_registry.json", registry)
    _write_json(compiled / "relations_schema.json", relation_schema)
    _write_json(compiled / "manifest.json", {
        "content_sha256": "test-digest",
        "source_file_count": 4,
        "entity_count": 1,
        "relation_count": 1,
    })

    monkeypatch.setattr(data.settings, "data_dir", tmp_path)
    data.clear_cache()
    try:
        assert data._load_all_entities_raw() == entities
        assert data._load_all_relations_raw() == relations
        assert data.load_schema_registry() == registry
        assert data.load_relations_schema() == relation_schema
        assert data._dir_signature(tmp_path) == ("test-digest", 4)
    finally:
        data.clear_cache()


def test_compiled_runtime_rejects_incomplete_bundle(monkeypatch, tmp_path):
    compiled = tmp_path / "_compiled"
    _write_json(compiled / "entities.json", [])
    _write_json(compiled / "manifest.json", {
        "content_sha256": "incomplete",
        "source_file_count": 1,
        "entity_count": 0,
        "relation_count": 0,
    })

    monkeypatch.setattr(data.settings, "data_dir", tmp_path)
    data.clear_cache()
    try:
        try:
            data._load_all_entities_raw()
        except RuntimeError as error:
            assert "relations.json" in str(error)
        else:
            raise AssertionError("incomplete compiled bundle must fail fast")
    finally:
        data.clear_cache()


def test_compiled_runtime_rejects_manifest_count_mismatch(monkeypatch, tmp_path):
    compiled = tmp_path / "_compiled"
    _write_json(compiled / "entities.json", [])
    _write_json(compiled / "relations.json", [])
    _write_json(compiled / "schema_registry.json", {})
    _write_json(compiled / "relations_schema.json", [])
    _write_json(compiled / "manifest.json", {
        "content_sha256": "wrong-count",
        "source_file_count": 4,
        "entity_count": 1,
        "relation_count": 0,
    })

    monkeypatch.setattr(data.settings, "data_dir", tmp_path)
    data.clear_cache()
    try:
        try:
            data._load_all_entities_raw()
        except ValueError as error:
            assert "entity_count mismatch" in str(error)
        else:
            raise AssertionError("compiled count mismatch must fail fast")
    finally:
        data.clear_cache()


def test_serverless_factory_uses_unprefixed_internal_routes():
    """EdgeOne 已把外部 /api/* 映射进函数，ASGI 内部路由必须去掉 /api。"""
    application = create_app(api_prefix="", mount_tiles=False)
    paths = {route.path for route in application.routes}

    assert "/meta/stats" in paths
    assert "/entities" in paths
    assert "/api/meta/stats" not in paths
    assert "/tiles/atlas" not in paths


def test_public_serverless_factory_omits_all_private_exploration_routes():
    application = create_app(
        api_prefix="",
        mount_tiles=False,
        enable_private_explorations=False,
    )
    paths = {route.path for route in application.routes}

    assert "/meta/stats" in paths
    assert not any(path.startswith("/explorations") for path in paths)

    root_route = next(route for route in application.routes if route.path == "/")
    root_payload = root_route.endpoint()
    assert not any("/explorations" in endpoint for endpoint in root_payload["endpoints"])
