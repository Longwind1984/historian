"""Territory service: return dated map records without inventing polity ownership."""
from __future__ import annotations

from functools import lru_cache
import json

from ..core.config import settings
from ..core.data import get_entity_index, load_geojson


CHGIS_RECORD_KIND = "chgis_prefecture"
POLITY_RECORD_KIND = "polity_territory"
CHGIS_RECORD_LABEL = "CHGIS府级行政建置记录"

_chgis_aggregate_cache: tuple[dict, ...] | None = None


def _as_year(value, default: int) -> int:
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return default


def _is_chgis_file(filename: str | None) -> bool:
    return bool(filename and filename.startswith("chgis_") and filename.endswith(".geojson"))


def _all_chgis_features() -> tuple[dict, ...]:
    """Load every CHGIS source file once and neutralize stale polity metadata."""
    global _chgis_aggregate_cache
    if _chgis_aggregate_cache is not None:
        return _chgis_aggregate_cache

    features = []
    seen_records = set()
    for path in sorted((settings.data_dir / "geo").glob("chgis_*.geojson")):
        gj = load_geojson(path.name)
        if not gj:
            continue
        for feature in gj.get("features") or []:
            props = dict(feature.get("properties") or {})
            record_key = json.dumps(
                {"properties": props, "geometry": feature.get("geometry")},
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
            )
            if record_key in seen_records:
                continue
            seen_records.add(record_key)
            # CHGIS DBF has administrative time-series records, but no polity field.
            # Filename-era bucketing is an import artifact and must not become a claim
            # that every prefecture in that file belonged to that polity.
            for key in ("polity_id", "polity_name", "polity_color"):
                props.pop(key, None)
            props.update({
                "record_kind": CHGIS_RECORD_KIND,
                "record_label": CHGIS_RECORD_LABEL,
                "source_name": "CHGIS V5",
                "source_file": path.name,
            })
            features.append({**feature, "properties": props})
    _chgis_aggregate_cache = tuple(features)
    return _chgis_aggregate_cache


@lru_cache(maxsize=512)
def _chgis_features_at(year: int) -> tuple[dict, ...]:
    """Filter CHGIS by record interval; bound arbitrary-year query memory."""
    return tuple(
        feature for feature in _all_chgis_features()
        if (_as_year((feature.get("properties") or {}).get("beg_yr"), -9999)
            <= year
            <= _as_year((feature.get("properties") or {}).get("end_yr"), 9999))
    )


def _active_non_chgis_segment(entity: dict, year: int | None) -> dict | None:
    """Pick the first active hand-drawn/peak segment, deliberately skipping CHGIS."""
    for segment in entity.get("territory") or []:
        filename = segment.get("geojson_file")
        if not filename or _is_chgis_file(filename):
            continue
        if year is None:
            return segment
        valid_from = _as_year((segment.get("valid_from") or {}).get("year"), -9999)
        valid_to = _as_year((segment.get("valid_to") or {}).get("year"), 9999)
        if valid_from <= year <= valid_to:
            return segment
    return None


def _polity_features(entity: dict, segment: dict, year: int | None) -> list[dict]:
    filename = segment.get("geojson_file")
    gj = load_geojson(filename)
    if not gj:
        return []
    return [
        {
            **feature,
            "properties": {
                **(feature.get("properties") or {}),
                "record_kind": POLITY_RECORD_KIND,
                "record_label": "政权疆域",
                "source_file": filename,
                "polity_id": entity.get("id"),
                "polity_name": entity.get("name"),
                "polity_color": entity.get("color", "#888888"),
                **({"year": year} if year is not None else {}),
            },
        }
        for feature in gj.get("features") or []
    ]


def territories_at(year: int) -> dict:
    """Return dated CHGIS admin records plus independently sourced polity territories."""
    chgis_features = [
        {
            **feature,
            "properties": {**(feature.get("properties") or {}), "year": year},
        }
        for feature in _chgis_features_at(year)
    ]
    polity_features = []
    for entity in get_entity_index().entities_by_type("Polity"):
        founded = (entity.get("founded") or {}).get("year")
        ended = (entity.get("ended") or {}).get("year")
        if founded is not None and year < founded:
            continue
        if ended is not None and year > ended:
            continue
        segment = _active_non_chgis_segment(entity, year)
        if segment:
            polity_features.extend(_polity_features(entity, segment, year))

    return {
        "type": "FeatureCollection",
        "year": year,
        "layers": {
            "chgis_admin_records": len(chgis_features),
            "polity_territories": len(polity_features),
        },
        "features": [*chgis_features, *polity_features],
    }


def polity_territory(polity_id: str, year: int | None = None) -> dict | None:
    """Return only independently sourced territory for one polity, never CHGIS buckets."""
    polity = get_entity_index().get(polity_id)
    if not polity or polity.get("type") != "Polity":
        return None
    segment = _active_non_chgis_segment(polity, year)
    if not segment:
        return {"type": "FeatureCollection", "features": []}
    return {
        "type": "FeatureCollection",
        "features": _polity_features(polity, segment, year),
    }
