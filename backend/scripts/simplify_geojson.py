"""
Simplify CHGIS GeoJSON polygons using Ramer-Douglas-Peucker.

Why: Tang dynasty file is 17 MB (871 polygons × avg 881 points = 768k points).
The frontend map freezes when downloading and rendering such large payloads.

Strategy: apply RDP with epsilon=0.01° (≈1.1 km) per polygon ring.
Aggressive enough to drop 90%+ of points while preserving shape.

Output: data/geo/chgis_<dynasty>.geojson is overwritten in place.
Originals are backed up to data/geo/originals/ on first run.
"""
from __future__ import annotations
import json
import shutil
import sys
from pathlib import Path
from typing import Sequence

ROOT = Path(__file__).resolve().parents[2]
GEO_DIR = ROOT / "data" / "geo"
BACKUP_DIR = GEO_DIR / "originals"

EPSILON = 0.01   # degrees, ≈1.1 km at mid-latitude
MIN_POINTS = 4   # never reduce below this (a triangle + closing point)


def perpendicular_distance(pt: Sequence[float], line_start: Sequence[float], line_end: Sequence[float]) -> float:
    """Shortest distance from pt to the line segment [line_start, line_end]."""
    x, y = pt
    x1, y1 = line_start
    x2, y2 = line_end
    dx, dy = x2 - x1, y2 - y1
    if dx == 0 and dy == 0:
        return ((x - x1) ** 2 + (y - y1) ** 2) ** 0.5
    t = ((x - x1) * dx + (y - y1) * dy) / (dx * dx + dy * dy)
    t = max(0.0, min(1.0, t))
    proj_x = x1 + t * dx
    proj_y = y1 + t * dy
    return ((x - proj_x) ** 2 + (y - proj_y) ** 2) ** 0.5


def rdp(points: list[list[float]], epsilon: float) -> list[list[float]]:
    """Ramer-Douglas-Peucker simplification. Preserves first & last point."""
    if len(points) <= MIN_POINTS:
        return points
    # Find point with max distance from line connecting endpoints
    start, end = points[0], points[-1]
    max_dist = 0.0
    max_idx = 0
    for i in range(1, len(points) - 1):
        d = perpendicular_distance(points[i], start, end)
        if d > max_dist:
            max_dist = d
            max_idx = i
    # Recurse if max distance exceeds epsilon
    if max_dist > epsilon:
        left = rdp(points[:max_idx + 1], epsilon)
        right = rdp(points[max_idx:], epsilon)
        return left[:-1] + right
    else:
        return [start, end]


def simplify_ring(ring: list[list[float]], epsilon: float) -> list[list[float]]:
    """Simplify a closed ring. RDP on the open chain, then re-close."""
    if len(ring) <= MIN_POINTS:
        return ring
    # Drop closing point, simplify, re-close
    simplified = rdp(ring[:-1], epsilon)
    if simplified[0] != simplified[-1]:
        simplified.append(simplified[0])
    return simplified


def simplify_geometry(geom: dict, epsilon: float) -> dict:
    gtype = geom.get('type')
    coords = geom.get('coordinates')
    if gtype == 'Polygon':
        new_rings = [simplify_ring(r, epsilon) for r in coords]
        return {'type': 'Polygon', 'coordinates': new_rings}
    elif gtype == 'MultiPolygon':
        new_polys = []
        for poly in coords:
            new_polys.append([simplify_ring(r, epsilon) for r in poly])
        return {'type': 'MultiPolygon', 'coordinates': new_polys}
    return geom


def main():
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)

    chgis_files = sorted(GEO_DIR.glob('chgis_*.geojson'))
    if not chgis_files:
        sys.exit('No chgis_*.geojson files found')

    total_before = 0
    total_after = 0

    for path in chgis_files:
        # Backup original once
        backup = BACKUP_DIR / path.name
        if not backup.exists():
            shutil.copy2(path, backup)
            print(f'  ✓ backed up {path.name} → originals/')

        with open(backup, encoding='utf-8') as f:
            data = json.load(f)

        # Count original points
        before_pts = 0
        for feat in data['features']:
            geom = feat['geometry']
            if geom['type'] == 'Polygon':
                for r in geom['coordinates']:
                    before_pts += len(r)
            else:
                for poly in geom['coordinates']:
                    for r in poly:
                        before_pts += len(r)

        # Simplify each feature
        after_pts = 0
        for feat in data['features']:
            feat['geometry'] = simplify_geometry(feat['geometry'], EPSILON)
            geom = feat['geometry']
            if geom['type'] == 'Polygon':
                for r in geom['coordinates']:
                    after_pts += len(r)
            else:
                for poly in geom['coordinates']:
                    for r in poly:
                        after_pts += len(r)

        # Write simplified version
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False)

        ratio = (1 - after_pts / before_pts) * 100 if before_pts else 0
        size_kb = path.stat().st_size // 1024
        backup_kb = backup.stat().st_size // 1024
        print(f'  ✓ {path.name}: {before_pts:>6} → {after_pts:>6} pts  '
              f'({ratio:.1f}% reduced)  '
              f'{backup_kb} KB → {size_kb} KB')
        total_before += before_pts
        total_after += after_pts

    print(f'\n✅ Total: {total_before:,} → {total_after:,} points '
          f'({(1 - total_after/total_before)*100:.1f}% reduction)')
    print(f'   Originals preserved in: {BACKUP_DIR}')


if __name__ == '__main__':
    main()
