"""API 合同测试：CHGIS 行政记录与政权疆域保持语义分层。"""
import json
from pathlib import Path

from fastapi.testclient import TestClient


def _props_of_kind(body: dict, kind: str) -> list[dict]:
    return [
        feature.get("properties") or {}
        for feature in body.get("features") or []
        if (feature.get("properties") or {}).get("record_kind") == kind
    ]


def _positions(obj):
    if isinstance(obj, dict):
        if "coordinates" in obj:
            yield from _positions(obj["coordinates"])
        for geometry in obj.get("geometries") or []:
            yield from _positions(geometry)
    elif isinstance(obj, list):
        if len(obj) >= 2 and all(isinstance(x, (int, float)) for x in obj[:2]):
            yield obj[0], obj[1]
        else:
            for child in obj:
                yield from _positions(child)


def test_territories_750(client: TestClient):
    """750 年只返回各记录自身时段覆盖该年的 CHGIS 府级记录。"""
    r = client.get("/api/territories", params={"year": 750})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["type"] == "FeatureCollection"
    assert body["year"] == 750
    admin = _props_of_kind(body, "chgis_prefecture")
    assert len(admin) >= 140
    assert body["layers"]["chgis_admin_records"] == len(admin)
    assert all(p["beg_yr"] <= 750 <= p["end_yr"] for p in admin)
    assert all(p["record_label"] == "CHGIS府级行政建置记录" for p in admin)
    assert all("polity_id" not in p and "polity_color" not in p for p in admin)


def test_territories_minus_215_filters_current_records(client: TestClient):
    """前 215 年的 10 条是抽取窗口全集；真正仍有效的只有 4 条。"""
    r = client.get("/api/territories", params={"year": -215})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["type"] == "FeatureCollection"
    admin = _props_of_kind(body, "chgis_prefecture")
    assert len(admin) == 4
    assert all(p["beg_yr"] <= -215 <= p["end_yr"] for p in admin)


def test_1050_southern_prefectures_are_not_labeled_liao(client: TestClient):
    """CHGIS 文件名不能把福州、泉州、杭州伪装成辽朝疆域。"""
    body = client.get("/api/territories", params={"year": 1050}).json()
    southern = [
        p for p in _props_of_kind(body, "chgis_prefecture")
        if p.get("name_ch") in {"福州", "泉州", "杭州"}
    ]
    assert {p["name_ch"] for p in southern} == {"福州", "泉州", "杭州"}
    assert all("polity_id" not in p for p in southern)
    assert not any(
        p.get("name_ch") in {"福州", "泉州", "杭州"} and p.get("polity_id") == "k_liao"
        for p in (f.get("properties") or {} for f in body["features"])
    )


def test_non_chgis_peak_territory_remains_polity_layer(client: TestClient):
    body = client.get("/api/territories", params={"year": 1050}).json()
    peaks = _props_of_kind(body, "polity_territory")
    assert any(
        p.get("source_file") == "liao_peak.geojson" and p.get("polity_id") == "k_liao"
        for p in peaks
    )
    assert body["layers"]["polity_territories"] == len(peaks)


def test_all_chgis_geojson_coordinates_are_wgs84():
    geo_dir = Path(__file__).resolve().parents[2] / "data" / "geo"
    checked = 0
    for path in sorted(geo_dir.glob("chgis_*.geojson")):
        data = json.loads(path.read_text(encoding="utf-8"))
        for feature in data.get("features") or []:
            for lon, lat in _positions(feature.get("geometry") or {}):
                checked += 1
                assert -180 <= lon <= 180, f"{path.name}: invalid longitude {lon}"
                assert -90 <= lat <= 90, f"{path.name}: invalid latitude {lat}"
    assert checked > 0


def test_chgis_aggregate_preserves_distinct_geometry_parts():
    """同一 sys_id/时段可有多个不同 polygon，不能按属性三元组误删。"""
    from app.services.territory_service import _all_chgis_features

    geo_dir = Path(__file__).resolve().parents[2] / "data" / "geo"
    exact_signatures = set()
    expected_parts = set()
    for path in sorted(geo_dir.glob("chgis_*.geojson")):
        data = json.loads(path.read_text(encoding="utf-8"))
        for feature in data.get("features") or []:
            props = feature.get("properties") or {}
            signature = json.dumps(
                {"properties": props, "geometry": feature.get("geometry")},
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
            )
            exact_signatures.add(signature)
            if str(props.get("sys_id")) == "79615":
                expected_parts.add(json.dumps(feature.get("geometry"), sort_keys=True))

    aggregated = _all_chgis_features()
    actual_parts = {
        json.dumps(feature.get("geometry"), sort_keys=True)
        for feature in aggregated
        if str((feature.get("properties") or {}).get("sys_id")) == "79615"
    }
    assert len(aggregated) == len(exact_signatures) == 3062
    assert actual_parts == expected_parts
    assert len(actual_parts) == 6


def test_chgis_year_cache_is_bounded():
    """API 接受任意整数年；逐年缓存必须有上限，不能被查询撑到无限增长。"""
    from app.services.territory_service import _chgis_features_at

    assert _chgis_features_at.cache_parameters()["maxsize"] == 512
