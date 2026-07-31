"""Smoke test for backend.

Tests:
- All schema files load
- All YAML data files load and validate basic shape
- FastAPI app initializes
- Each API endpoint returns 200 on basic queries

Usage:
    cd backend && python -m pytest tests/test_smoke.py -v
    # or simply:
    python tests/test_smoke.py
"""
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))  # so `app` is importable

import yaml
from fastapi.testclient import TestClient


def test_schemas_load():
    schema_dir = HERE.parent.parent / "schema"
    schemas = {}
    for path in sorted(schema_dir.glob("*.yaml")):
        if path.name.startswith("_"):
            continue
        with open(path) as f:
            data = yaml.safe_load(f)
        assert data is not None, f"{path} is empty"
        if path.name == "relations.yaml":
            assert isinstance(data.get("relations"), list)
        else:
            assert "type" in data, f"{path} missing 'type'"
            schemas[data["type"]] = data
    # at least 6 node types
    assert len(schemas) >= 6, f"only {len(schemas)} node types"
    print(f"✓ {len(schemas)} node type schemas loaded")


def test_data_loads():
    data_dir = HERE.parent.parent / "data"
    entities_dir = data_dir / "entities"
    if not entities_dir.exists():
        print("⚠ data/entities not yet populated — skipping")
        return
    count = 0
    for type_dir in entities_dir.iterdir():
        if not type_dir.is_dir():
            continue
        for path in type_dir.glob("*.yaml"):
            with open(path) as f:
                data = yaml.safe_load(f)
            assert data is not None, f"{path} empty"
            assert "id" in data and "type" in data, f"{path} missing id/type"
            count += 1
    print(f"✓ {count} entity YAMLs parsed")


def test_app():
    from app.main import app
    client = TestClient(app)
    r = client.get("/")
    assert r.status_code == 200, r.text
    body = r.json()
    assert "name" in body

    r = client.get("/api/meta/schema")
    assert r.status_code == 200, r.text
    schema = r.json()
    assert "node_types" in schema
    print(f"✓ /api/meta/schema returns {len(schema['node_types'])} node types")

    r = client.get("/api/meta/stats")
    assert r.status_code == 200, r.text
    print(f"✓ /api/meta/stats: {r.json()}")

    r = client.get("/api/entities")
    assert r.status_code == 200, r.text
    body = r.json()
    assert "items" in body
    print(f"✓ /api/entities returns {body['total']} entities")

    r = client.get("/api/timeline", params={"from": 900, "to": 1000})
    assert r.status_code == 200, r.text
    print(f"✓ /api/timeline returns {r.json()['total']} events")

    r = client.get("/api/territories", params={"year": 947})
    assert r.status_code == 200, r.text
    print(f"✓ /api/territories?year=947 returns {len(r.json().get('features', []))} features")


if __name__ == "__main__":
    print("=== Smoke test ===")
    test_schemas_load()
    test_data_loads()
    test_app()
    print("\n✅ All smoke tests passed")
