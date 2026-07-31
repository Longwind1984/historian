"""
CHGIS V5 → GeoJSON transformer
==============================

运行（专用依赖由 uv 放进临时环境，不进入后端运行时）：
  uv run --with-requirements scripts/requirements-chgis.txt python3 backend/scripts/import_chgis.py

Reads CHGIS V5 time-series prefecture polygons (v5_time_pref_pgn_utf.shp),
reprojects from Gauss-Kruger (CM=111, false_easting=19500000) to WGS84,
and emits per-dynasty GeoJSON files compatible with our Polity.territory schema.

Output:
  data/geo/chgis_<dynasty>.geojson         # one FeatureCollection per dynasty
  data/geo/chgis_<dynasty>_<period>.geojson # if a dynasty has multiple periods

The Polity YAMLs' `territory` field is then patched to point to these files.

Strategy notes:
  - CHGIS provides BEG_YR/END_YR per polygon; we slice by dynasty start year.
  - A polygon belongs to a dynasty if [BEG_YR, END_YR] overlaps the dynasty's range.
  - We union (dissolve) all prefectures of the same dynasty into one FeatureCollection.
"""
from __future__ import annotations
import json
import sys
from pathlib import Path
import shapefile
from pyproj import Transformer

ROOT = Path(__file__).resolve().parents[2]
SHP_PATH = ROOT / "external_data" / "chgis_v5" / "v5_time_pref_pgn_utf.shp"
GEO_DIR = ROOT / "data" / "geo"
POLITIES_DIR = ROOT / "data" / "entities" / "polities"

# CHGIS uses China standard dynasty year ranges
# Each entry: dynasty_id (our polity id prefix), display name, year range, color
# Map to OUR polity IDs where possible; for unmapped dynasties, create a generic dynasty file.
DYNASTY_RANGES = [
    # (label, file_slug, year_start, year_end, polity_id_or_None)
    ("秦",         "qin",          -221, -206, "k_qin"),
    ("西汉",       "xihan",        -206, 9,    "k_xihan"),
    ("新",         "xin",          9,    23,   "k_xin"),
    ("东汉",       "donghan",      25,   220,  "k_donghan"),
    ("三国魏",     "caowei",       220,  265,  "k_caowei"),
    ("三国蜀",     "shuhan",       221,  263,  "k_shuhan"),
    ("三国吴",     "dongwu",       222,  280,  "k_dongwu"),
    ("西晋",       "xijin",        265,  316,  "k_xijin"),
    ("东晋十六国", "dongjin",      317,  419,  "k_dongjin"),
    ("南北朝",     "nanbeichao",   420,  589,  None),
    ("隋",         "sui",          581,  618,  "k_sui"),
    ("唐",         "tang",         618,  907,  "k_tang"),
    ("五代十国",   "wudai",        907,  960,  None),
    ("辽",         "liao",         947,  1125, "k_liao"),
    ("北宋",       "beisong",      960,  1127, "k_beisong"),
    ("南宋",       "nansong",      1127, 1279, None),
    ("金",         "jin",          1115, 1234, "k_jin"),
    ("西夏",       "xixia",        1032, 1227, "k_xixia"),
    ("元",         "yuan",         1271, 1368, "k_yuan"),
    ("明",         "ming",         1368, 1644, "k_ming"),
    ("清",         "qing",         1644, 1911, "k_qing"),
]

SRC_PROJ = '+proj=tmerc +lat_0=0 +lon_0=111 +k=1 +x_0=19500000 +y_0=0 +ellps=aust_SA +units=m +no_defs'


def shp_to_geojson_features() -> list[dict]:
    """Read shapefile and return list of GeoJSON Features in WGS84."""
    print(f"Reading {SHP_PATH}...")
    sf = shapefile.Reader(str(SHP_PATH), encoding='utf-8')
    transformer = Transformer.from_crs(SRC_PROJ, 'EPSG:4326', always_xy=True)

    features = []
    skipped = 0
    for i, rec in enumerate(sf.records()):
        d = rec.as_dict()
        beg = d.get('BEG_YR')
        end = d.get('END_YR')
        if beg is None or end is None or beg <= -9999 or end <= -9999:
            skipped += 1
            continue

        shape = sf.shape(i)
        if not shape.points:
            continue

        # Build polygon(s) from parts
        polygons = []
        parts_idx = list(shape.parts) + [len(shape.points)]
        for pi in range(len(parts_idx) - 1):
            start, stop = parts_idx[pi], parts_idx[pi + 1]
            ring_pts = shape.points[start:stop]
            if len(ring_pts) < 4:
                continue
            # Reproject each point
            ring = []
            xs = [p[0] for p in ring_pts]
            ys = [p[1] for p in ring_pts]
            lons, lats = transformer.transform(xs, ys)
            for lon, lat in zip(lons, lats):
                ring.append([round(lon, 5), round(lat, 5)])
            # Ensure closed
            if ring[0] != ring[-1]:
                ring.append(ring[0])
            polygons.append(ring)

        if not polygons:
            continue

        geometry = {
            "type": "Polygon" if len(polygons) == 1 else "MultiPolygon",
        }
        if len(polygons) == 1:
            geometry["coordinates"] = [polygons[0]]
        else:
            geometry["coordinates"] = [[poly] for poly in polygons]

        feature = {
            "type": "Feature",
            "properties": {
                "sys_id": d.get('SYS_ID'),
                "name_py": d.get('NAME_PY'),
                "name_ch": d.get('NAME_CH'),
                "name_ft": d.get('NAME_FT'),
                "type_ch": d.get('TYPE_CH'),
                "beg_yr": int(beg),
                "end_yr": int(end),
                "x_coord": d.get('X_COORD'),
                "y_coord": d.get('Y_COORD'),
            },
            "geometry": geometry,
        }
        features.append(feature)

    print(f"✓ Parsed {len(features)} features ({skipped} skipped for missing years)")
    return features


def slice_by_dynasty(features: list[dict]) -> dict[str, list[dict]]:
    """Bucket features by dynasty. A feature goes into the dynasty whose range
    contains its midpoint year (= avg(beg, end))."""
    by_dynasty: dict[str, list[dict]] = {slug: [] for _, slug, _, _, _ in DYNASTY_RANGES}
    unassigned = []

    for feat in features:
        beg = feat["properties"]["beg_yr"]
        end = feat["properties"]["end_yr"]
        mid = (beg + end) // 2
        assigned = False
        for label, slug, ystart, yend, _ in DYNASTY_RANGES:
            if ystart <= mid <= yend:
                by_dynasty[slug].append(feat)
                assigned = True
                break
        if not assigned:
            unassigned.append(feat)

    if unassigned:
        # show distribution of unassigned midpoints
        from collections import Counter
        c = Counter()
        for f in unassigned:
            mid = (f["properties"]["beg_yr"] + f["properties"]["end_yr"]) // 2
            bucket = (mid // 100) * 100
            c[bucket] += 1
        print(f"⚠ {len(unassigned)} features unassigned by midpoint year. Distribution:")
        for yr, cnt in sorted(c.items()):
            print(f"    ~{yr} AD: {cnt}")

    return by_dynasty


def write_geojsons(by_dynasty: dict[str, list[dict]]) -> dict[str, str]:
    """Write each dynasty bucket to a GeoJSON file. Returns slug → filename."""
    written = {}
    for slug, feats in by_dynasty.items():
        if not feats:
            continue
        fname = f"chgis_{slug}.geojson"
        out = {
            "type": "FeatureCollection",
            "source": "CHGIS V5 (Harvard/Fudan 2012)",
            "feature_count": len(feats),
            "features": feats,
        }
        path = GEO_DIR / fname
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(out, f, ensure_ascii=False)
        written[slug] = fname
        print(f"  ✓ {fname}: {len(feats)} features")
    return written


def patch_polities(slug_to_file: dict[str, str]) -> int:
    """For each dynasty whose polity_id is known, add/update the territory
    reference in the polity YAML. Returns count of polities patched."""
    import yaml

    patched = 0
    # Build a lookup: polity_id → (slug, filename, year_start, year_end)
    polity_to_geo = {}
    for label, slug, ystart, yend, polity_id in DYNASTY_RANGES:
        if polity_id and slug in slug_to_file:
            polity_to_geo[polity_id] = (slug_to_file[slug], ystart, yend)

    if not polity_to_geo:
        return 0

    # Backup existing files first (idempotent: we add a CHGIS segment if missing)
    for polity_file in sorted(POLITIES_DIR.glob("*.yaml")):
        with open(polity_file, encoding='utf-8') as f:
            d = yaml.safe_load(f)
        if not d:
            continue
        pid = d.get('id')
        if pid not in polity_to_geo:
            continue
        fname, ystart, yend = polity_to_geo[pid]

        territory = d.setdefault('territory', [])
        # Skip if a CHGIS reference is already present
        if any(seg.get('geojson_file', '').startswith('chgis_') for seg in territory):
            continue
        territory.insert(0, {
            'valid_from': {'year': ystart},
            'valid_to': {'year': yend},
            'geojson_file': fname,
            'note': 'CHGIS V5 prefecture polygons',
        })
        with open(polity_file, 'w', encoding='utf-8') as f:
            yaml.safe_dump(d, f, allow_unicode=True, sort_keys=False)
        patched += 1
        print(f"  ✓ patched {polity_file.name} → {fname}")

    return patched


def main():
    if not SHP_PATH.exists():
        sys.exit(f"❌ CHGIS shapefile not found at {SHP_PATH}")

    GEO_DIR.mkdir(parents=True, exist_ok=True)

    features = shp_to_geojson_features()
    by_dynasty = slice_by_dynasty(features)

    print(f"\n=== Writing per-dynasty GeoJSONs ===")
    slug_to_file = write_geojsons(by_dynasty)

    print(f"\n=== Patching Polity YAMLs ===")
    n = patch_polities(slug_to_file)
    print(f"\n✅ Done. {n} polities patched with CHGIS territory references.")
    print(f"   GeoJSON files in: {GEO_DIR}")


if __name__ == '__main__':
    main()
