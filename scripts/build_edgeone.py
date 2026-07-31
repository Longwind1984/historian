#!/usr/bin/env python3
"""Compile truth-source data into a compact EdgeOne deployment artifact."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import shutil

import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
PROFILE = os.getenv("EDGEONE_DISTRIBUTION_PROFILE", "full").strip().lower()
SAFE_PROFILE = PROFILE == "safe"
DATA_DIR = REPO_ROOT / "data"
SCHEMA_DIR = REPO_ROOT / "schema"
BACKEND_APP = REPO_ROOT / "backend" / "app"
FRONTEND_DIST = REPO_ROOT / "frontend" / "dist"
FUNCTION_TEMPLATE = REPO_ROOT / "cloud-functions"
OUTPUT_DIR = REPO_ROOT / ("edgeone-dist-safe" if SAFE_PROFILE else "edgeone-dist")
OUTPUT_FUNCTIONS = OUTPUT_DIR / "cloud-functions"
RUNTIME_DIR = OUTPUT_FUNCTIONS / "runtime_data"
COMPILED_DIR = RUNTIME_DIR / "_compiled"
ATLAS_SOURCE = DATA_DIR / "geo" / "atlas_tiles"
ATLAS_OUTPUT = OUTPUT_DIR / "tiles" / "atlas"
MAX_FUNCTION_SOURCE_BYTES = 96 * 1024 * 1024
MAX_DEPLOY_FILES = 20_000
MAX_STATIC_FILE_BYTES = 25 * 1024 * 1024
YAML_LOADER = getattr(yaml, "CSafeLoader", yaml.SafeLoader)


def read_yaml(path: Path):
    with path.open("r", encoding="utf-8") as file:
        return yaml.load(file, Loader=YAML_LOADER)


def write_json(path: Path, payload) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as file:
        json.dump(payload, file, ensure_ascii=False, separators=(",", ":"))
        file.write("\n")


def load_entities() -> tuple[list[dict], list[Path]]:
    entities, sources = [], []
    for type_dir in sorted((DATA_DIR / "entities").iterdir()):
        if not type_dir.is_dir():
            continue
        for path in sorted(type_dir.glob("*.yaml")):
            data = read_yaml(path) or {}
            if data and "type" in data:
                entities.append(data)
                sources.append(path)
    return entities, sources


def load_relations() -> tuple[list[dict], list[Path]]:
    relations, sources = [], []
    for path in sorted((DATA_DIR / "relations").glob("*.yaml")):
        data = read_yaml(path) or {}
        if isinstance(data, list):
            relations.extend(data)
        elif isinstance(data, dict) and "relations" in data:
            relations.extend(data["relations"])
        sources.append(path)
    return relations, sources


def load_schemas() -> tuple[dict[str, dict], list[dict], list[Path]]:
    registry, sources, relations_schema = {}, [], []
    for path in sorted(SCHEMA_DIR.glob("*.yaml")):
        if path.name.startswith("_"):
            continue
        data = read_yaml(path) or {}
        sources.append(path)
        if path.name == "relations.yaml":
            relations_schema = data.get("relations", [])
        elif "type" in data:
            registry[data["type"]] = data
    return registry, relations_schema, sources


def select_geojson_sources(profile: str = PROFILE) -> list[Path]:
    sources = sorted((DATA_DIR / "geo").glob("*.geojson"))
    if profile == "safe":
        return [path for path in sources if not path.name.startswith("chgis_")]
    return sources


def copy_geojson() -> list[Path]:
    geo_output = RUNTIME_DIR / "geo"
    geo_output.mkdir(parents=True, exist_ok=True)
    sources = select_geojson_sources()
    for source in sources:
        shutil.copy2(source, geo_output / source.name)
    return sources


def digest_files(paths: list[Path]) -> str:
    digest = hashlib.sha256()
    for path in sorted(paths):
        digest.update(path.relative_to(REPO_ROOT).as_posix().encode("utf-8"))
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def tree_stats(path: Path) -> tuple[int, int]:
    if not path.exists():
        return 0, 0
    files = [item for item in path.rglob("*") if item.is_file()]
    return len(files), sum(item.stat().st_size for item in files)


def validate_frontend_profile(frontend_dist: Path = FRONTEND_DIST) -> None:
    marker_path = frontend_dist / "distribution-profile.json"
    if not marker_path.is_file():
        raise RuntimeError(f"Frontend distribution marker is missing: {marker_path}")
    marker = json.loads(marker_path.read_text(encoding="utf-8"))
    actual = marker.get("distribution_profile")
    if actual != PROFILE:
        raise RuntimeError(
            f"Frontend distribution profile mismatch: expected={PROFILE} actual={actual}"
        )
    if marker.get("private_explorations_enabled") is not False:
        raise RuntimeError(
            "Public EdgeOne artifact requires private_explorations_enabled=false"
        )


def build() -> dict:
    if PROFILE not in {"full", "safe"}:
        raise RuntimeError(f"Unknown EdgeOne distribution profile: {PROFILE}")
    if SAFE_PROFILE and os.getenv("VITE_RESTRICTED_MAPS") != "0":
        raise RuntimeError(
            "safe profile requires VITE_RESTRICTED_MAPS=0 during the frontend build"
        )
    if not (FRONTEND_DIST / "index.html").is_file():
        raise RuntimeError("frontend/dist is missing; run the Vite build first")
    validate_frontend_profile()
    if OUTPUT_DIR.exists():
        shutil.rmtree(OUTPUT_DIR)
    shutil.copytree(FRONTEND_DIST, OUTPUT_DIR)
    shutil.copytree(FUNCTION_TEMPLATE, OUTPUT_FUNCTIONS)
    # Direct Upload 接收的是已经构建好的成品。不能把源码仓库的 buildCommand
    # 原样放进产物，否则云端会在成品目录里再次寻找 frontend/ 与 scripts/。
    write_json(OUTPUT_DIR / "package.json", {
        "name": "history-kb-edgeone-artifact",
        "private": True,
    })
    headers = [
        {
            "source": "/assets/*",
            "headers": [{
                "key": "Cache-Control",
                "value": "public, max-age=31536000, immutable",
            }],
        },
        {
            "source": "/release.json",
            "headers": [{
                "key": "Cache-Control",
                "value": "no-cache, no-store, must-revalidate",
            }],
        },
    ]
    if not SAFE_PROFILE:
        headers.append({
            "source": "/tiles/atlas/*",
            "headers": [{
                "key": "Cache-Control",
                "value": "public, max-age=86400",
            }],
        })
    write_json(OUTPUT_DIR / "edgeone.json", {
        "cloudFunctions": {"python": {"maxDuration": 60}},
        "headers": headers,
    })

    entities, entity_sources = load_entities()
    relations, relation_sources = load_relations()
    schema_registry, relations_schema, schema_sources = load_schemas()
    geo_sources = copy_geojson()
    write_json(COMPILED_DIR / "entities.json", entities)
    write_json(COMPILED_DIR / "relations.json", relations)
    write_json(COMPILED_DIR / "schema_registry.json", schema_registry)
    write_json(COMPILED_DIR / "relations_schema.json", relations_schema)

    source_paths = [*entity_sources, *relation_sources, *schema_sources, *geo_sources]
    excluded = ["data/geo/originals/**", "data/_align/**", "external_data/**"]
    if SAFE_PROFILE:
        excluded.extend([
            "data/geo/chgis_*.geojson (redistribution permission not established)",
            "data/geo/atlas_tiles/** (mirror redistribution permission not established)",
        ])
    else:
        excluded.insert(0, "data/geo/atlas_tiles/** (served as static assets)")
    manifest = {
        "format_version": 1,
        "distribution_profile": PROFILE,
        "content_sha256": digest_files(source_paths),
        "source_file_count": len(source_paths),
        "entity_count": len(entities),
        "relation_count": len(relations),
        "geojson_count": len(geo_sources),
        "excluded": excluded,
    }
    write_json(COMPILED_DIR / "manifest.json", manifest)
    shutil.copytree(BACKEND_APP, OUTPUT_FUNCTIONS / "history_app", ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    if not SAFE_PROFILE:
        shutil.copytree(ATLAS_SOURCE, ATLAS_OUTPUT)

    function_files, function_bytes = tree_stats(OUTPUT_FUNCTIONS)
    deploy_files, deploy_bytes = tree_stats(OUTPUT_DIR)
    atlas_files, atlas_bytes = tree_stats(ATLAS_OUTPUT)
    if function_bytes > MAX_FUNCTION_SOURCE_BYTES:
        raise RuntimeError(f"Cloud-function source exceeds 96 MiB safety budget: {function_bytes / 1024 / 1024:.1f} MiB")
    if deploy_files > MAX_DEPLOY_FILES:
        raise RuntimeError(f"Deployment has {deploy_files} files; EdgeOne limit is {MAX_DEPLOY_FILES}")
    oversized = [path for path in OUTPUT_DIR.rglob("*") if path.is_file() and "cloud-functions" not in path.parts and path.stat().st_size > MAX_STATIC_FILE_BYTES]
    if oversized:
        raise RuntimeError(f"Static files exceed 25 MiB: {oversized[:3]}")

    print(f"[edgeone] profile={PROFILE}")
    print(f"[edgeone] runtime: entities={len(entities)} relations={len(relations)} geojson={len(geo_sources)} files={function_files} mb={function_bytes / 1024 / 1024:.2f}")
    print(f"[edgeone] atlas: files={atlas_files} mb={atlas_bytes / 1024 / 1024:.2f}")
    print(f"[edgeone] deploy: files={deploy_files} mb={deploy_bytes / 1024 / 1024:.2f} output={OUTPUT_DIR.name}")
    return {**manifest, "function_source_files": function_files, "function_source_bytes": function_bytes, "atlas_static_files": atlas_files, "atlas_static_bytes": atlas_bytes, "deploy_files": deploy_files, "deploy_bytes": deploy_bytes}


if __name__ == "__main__":
    build()
