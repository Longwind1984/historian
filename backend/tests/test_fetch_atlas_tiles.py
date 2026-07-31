"""图砖抓取器的超时/熔断合同。"""
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
import urllib.error


ROOT = Path(__file__).resolve().parents[2]
SPEC = spec_from_file_location("fetch_atlas_tiles", ROOT / "scripts/fetch_atlas_tiles.py")
fetch_atlas_tiles = module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(fetch_atlas_tiles)


def test_network_failure_is_not_retried_and_breaks_pending_queue(monkeypatch, tmp_path):
    calls = 0

    def unavailable(*args, **kwargs):
        nonlocal calls
        calls += 1
        raise TimeoutError("host timeout")

    monkeypatch.setattr(fetch_atlas_tiles, "OUT", tmp_path)
    monkeypatch.setattr(fetch_atlas_tiles.urllib.request, "urlopen", unavailable)
    fetch_atlas_tiles._fetch_abort.clear()

    assert fetch_atlas_tiles.fetch(("mp_test", 2, 1, 1)) == -2
    assert fetch_atlas_tiles.fetch(("mp_test", 2, 1, 2)) == -2
    assert calls == 1


def test_http_missing_tile_does_not_trip_host_circuit_breaker(monkeypatch, tmp_path):
    calls = 0

    def missing(url, **kwargs):
        nonlocal calls
        calls += 1
        raise urllib.error.HTTPError(url, 404, "not found", {}, None)

    monkeypatch.setattr(fetch_atlas_tiles, "OUT", tmp_path)
    monkeypatch.setattr(fetch_atlas_tiles.urllib.request, "urlopen", missing)
    fetch_atlas_tiles._fetch_abort.clear()

    assert fetch_atlas_tiles.fetch(("mp_test", 2, 1, 1)) == -1
    assert fetch_atlas_tiles.fetch(("mp_test", 2, 1, 2)) == -1
    assert calls == 2
    assert not fetch_atlas_tiles._fetch_abort.is_set()
