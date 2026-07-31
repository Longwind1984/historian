#!/usr/bin/env python3
"""从 CHGIS V5 府级 polygon shapefile 按年窗抽取疆域为 GeoJSON。

为什么要有它:data/geo/chgis_*.geojson 此前是逐份手工产出的,仓库无抽取脚本 ——
于是「秦只导了 7/10 府」这类截断无从复现也无从体检。本脚本把「年窗 → 活跃府 → GeoJSON」
固化成一条可复跑的管线,与 territory_service.territories_at 同口径(按 BEG_YR/END_YR
的时段相交判活跃)。

数据源:external_data/chgis_v5/v5_time_pref_pgn_utf.shp(哈佛+复旦,CC BY-NC-SA)。
郡县制是秦的发明,故该数据集最早只到 BEG_YR≈-224 —— 先秦(战国及以前)本就无府级 polygon,
不是抽取遗漏。先秦疆域走谭其骧「古」栅格图集,不在此列。

property schema 与既有 chgis_*.geojson 对齐:sys_id/name_py/name_ch/name_ft/
type_ch/beg_yr/end_yr/x_coord/y_coord —— 前端与 territory_service 都不依赖多余字段。

用法:
  # 专用依赖由 uv 放进临时环境，不进入 backend 生产环境
  # 干跑:只列年窗内活跃府,不写文件
  uv run --with-requirements scripts/requirements-chgis.txt python3 scripts/extract_chgis.py --from -221 --to -207 --dry
  # 写出(幂等覆盖)
  uv run --with-requirements scripts/requirements-chgis.txt python3 scripts/extract_chgis.py --from -221 --to -207 -o data/geo/chgis_qin.geojson
  # 只追加缺失 sys_id(不动既有 feature 的几何)
  uv run --with-requirements scripts/requirements-chgis.txt python3 scripts/extract_chgis.py --from -221 --to -207 --into data/geo/chgis_qin.geojson
"""
from __future__ import annotations

import argparse
import json
import pathlib
import sys

import shapefile  # pyshp
from pyproj import Transformer

ROOT = pathlib.Path(__file__).resolve().parent.parent
SHP = ROOT / "external_data" / "chgis_v5" / "v5_time_pref_pgn_utf"

# CHGIS V5 原始 shp 不是经纬度，而是 Gauss-Kruger 米制坐标。旧导入器
# backend/scripts/import_chgis.py 使用的也是这组参数；若直接把
# shape.__geo_interface__ 当 WGS84，MapLibre 会收到 x≈20,000,000 的无效经度。
SRC_PROJ = (
    "+proj=tmerc +lat_0=0 +lon_0=111 +k=1 +x_0=19500000 +y_0=0 "
    "+ellps=aust_SA +units=m +no_defs"
)
TO_WGS84 = Transformer.from_crs(SRC_PROJ, "EPSG:4326", always_xy=True)

# 输出保留的属性(与既有 geojson 一致);key 是 GeoJSON 里的小写名,value 是 DBF 字段名
PROP_MAP = {
    "sys_id": "SYS_ID", "name_py": "NAME_PY", "name_ch": "NAME_CH",
    "name_ft": "NAME_FT", "type_ch": "TYPE_CH", "beg_yr": "BEG_YR",
    "end_yr": "END_YR", "x_coord": "X_COORD", "y_coord": "Y_COORD",
}


def _yi(v):
    try:
        return int(float(v))
    except (TypeError, ValueError):
        return None


def _to_wgs84_coords(obj, nd=5):
    """递归把 GeoJSON 坐标从 CHGIS Gauss-Kruger 转为 WGS84，并取 5 位小数。"""
    if isinstance(obj, (list, tuple)):
        if (len(obj) >= 2
                and isinstance(obj[0], (int, float)) and not isinstance(obj[0], bool)
                and isinstance(obj[1], (int, float)) and not isinstance(obj[1], bool)):
            lon, lat = TO_WGS84.transform(obj[0], obj[1])
            tail = [round(x, nd) if isinstance(x, (int, float)) else x for x in obj[2:]]
            return [round(lon, nd), round(lat, nd), *tail]
        return [_to_wgs84_coords(x, nd) for x in obj]
    return obj


def extract(lo: int, hi: int) -> list[dict]:
    """返回年窗 [lo, hi] 内活跃(时段相交)的府 feature 列表,按 beg_yr 升序。"""
    r = shapefile.Reader(str(SHP))
    flds = [f[0] for f in r.fields[1:]]
    idx = {name: flds.index(dbf) for name, dbf in PROP_MAP.items()}
    feats = []
    for sr in r.iterShapeRecords():
        rec = sr.record
        b = _yi(rec[idx["beg_yr"]])
        e = _yi(rec[idx["end_yr"]])
        if b is None:
            continue
        if e is None:
            e = 9999
        if not (b <= hi and e >= lo):
            continue
        props = {}
        for name, _dbf in PROP_MAP.items():
            v = rec[idx[name]]
            props[name] = _yi(v) if name in ("beg_yr", "end_yr") else v
        geom = sr.shape.__geo_interface__
        geom = {**geom, "coordinates": _to_wgs84_coords(geom.get("coordinates"))}
        feats.append({
            "type": "Feature",
            "properties": props,
            "geometry": geom,
        })
    feats.sort(key=lambda f: (f["properties"]["beg_yr"], str(f["properties"]["sys_id"])))
    return feats


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--from", dest="lo", type=int, required=True)
    ap.add_argument("--to", dest="hi", type=int, required=True)
    ap.add_argument("-o", "--out", help="写出到此文件(整体覆盖)")
    ap.add_argument("--into", help="只把缺失 sys_id 追加进此文件(既有 feature 不动)")
    ap.add_argument(
        "--replace-geometry",
        help="与 --into 同用：逗号分隔 sys_id，只替换这些既有 feature 的 geometry",
    )
    ap.add_argument("--dry", action="store_true", help="只列清单不写")
    a = ap.parse_args()

    if a.replace_geometry and not a.into:
        ap.error("--replace-geometry 必须与 --into 同用")

    feats = extract(a.lo, a.hi)
    print(f"年窗 [{a.lo}..{a.hi}] 活跃 {len(feats)} 府:", file=sys.stderr)
    for f in feats:
        p = f["properties"]
        print(f"  sys_id={p['sys_id']:<8} {p['name_ch']} ({p['type_ch']}) "
              f"{p['beg_yr']}..{p['end_yr']}", file=sys.stderr)

    if a.dry:
        return

    if a.into:
        path = pathlib.Path(a.into)
        fc = json.loads(path.read_text(encoding="utf-8"))
        have = {str(x["properties"].get("sys_id")) for x in fc["features"]}
        added = [f for f in feats if str(f["properties"]["sys_id"]) not in have]
        fc["features"].extend(added)
        replaced = 0
        if a.replace_geometry:
            wanted = {x.strip() for x in a.replace_geometry.split(",") if x.strip()}
            extracted = {str(f["properties"]["sys_id"]): f for f in feats}
            missing_source = wanted - extracted.keys()
            missing_target = wanted - have
            if missing_source or missing_target:
                problems = []
                if missing_source:
                    problems.append(f"年窗未抽到: {sorted(missing_source)}")
                if missing_target:
                    problems.append(f"目标文件不存在: {sorted(missing_target)}")
                raise SystemExit("拒绝替换 geometry：" + "；".join(problems))
            for old in fc["features"]:
                sid = str((old.get("properties") or {}).get("sys_id"))
                if sid in wanted:
                    old["geometry"] = extracted[sid]["geometry"]
                    replaced += 1
        path.write_text(json.dumps(fc, ensure_ascii=False), encoding="utf-8")
        print(f"追加 {len(added)} 块、替换 geometry {replaced} 块 → "
              f"{path}(现共 {len(fc['features'])} 块)")
        return

    if a.out:
        fc = {"type": "FeatureCollection", "features": feats}
        pathlib.Path(a.out).write_text(json.dumps(fc, ensure_ascii=False), encoding="utf-8")
        print(f"写出 {len(feats)} 块 → {a.out}")


if __name__ == "__main__":
    main()
