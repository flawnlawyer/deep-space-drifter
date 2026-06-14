"""
tests/test_pipeline.py
Full pipeline tests using real TLE fixtures (no network calls).
Run: python -m pytest tests/ -v
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.fetch import _parse_tle_text
from core.propagate import build_satellite, get_position, get_positions_bulk, get_pass_window

# ── Real TLE fixtures (valid as of mid-2025, good enough for unit tests) ─────

ISS_TLE = {
    "name":  "ISS (ZARYA)",
    "line1": "1 25544U 98067A   25150.50000000  .00020000  00000-0  35000-3 0  9993",
    "line2": "2 25544  51.6400 120.0000 0001000  90.0000 270.0000 15.49000000500000",
}

HUBBLE_TLE = {
    "name":  "HST",
    "line1": "1 20580U 90037B   25150.50000000  .00001000  00000-0  50000-4 0  9991",
    "line2": "2 20580  28.4700 200.0000 0002000  60.0000 300.0000 15.09000000200000",
}

RAW_TLE_TEXT = """ISS (ZARYA)
1 25544U 98067A   25150.50000000  .00020000  00000-0  35000-3 0  9993
2 25544  51.6400 120.0000 0001000  90.0000 270.0000 15.49000000500000
HST
1 20580U 90037B   25150.50000000  .00001000  00000-0  50000-4 0  9991
2 20580  28.4700 200.0000 0002000  60.0000 300.0000 15.09000000200000
"""

MALFORMED_TLE_TEXT = """BROKEN ENTRY
not a valid line 1
not a valid line 2
ISS (ZARYA)
1 25544U 98067A   25150.50000000  .00020000  00000-0  35000-3 0  9993
2 25544  51.6400 120.0000 0001000  90.0000 270.0000 15.49000000500000
"""


# ── Parser tests ──────────────────────────────────────────────────────────────

def test_parse_tle_text_count():
    sats = _parse_tle_text(RAW_TLE_TEXT)
    assert len(sats) == 2, f"Expected 2 satellites, got {len(sats)}"

def test_parse_tle_text_fields():
    sats = _parse_tle_text(RAW_TLE_TEXT)
    iss = sats[0]
    assert iss["name"] == "ISS (ZARYA)"
    assert iss["line1"].startswith("1 ")
    assert iss["line2"].startswith("2 ")

def test_parse_skips_malformed():
    sats = _parse_tle_text(MALFORMED_TLE_TEXT)
    assert len(sats) == 1
    assert sats[0]["name"] == "ISS (ZARYA)"

def test_parse_empty_string():
    sats = _parse_tle_text("")
    assert sats == []


# ── Propagator tests ──────────────────────────────────────────────────────────

def test_build_satellite():
    sat = build_satellite(ISS_TLE)
    assert sat.name == "ISS (ZARYA)"

def test_get_position_fields():
    sat = build_satellite(ISS_TLE)
    pos = get_position(sat)
    assert "lat" in pos
    assert "lon" in pos
    assert "alt_km" in pos
    assert "speed_kms" in pos
    assert "epoch" in pos

def test_get_position_lat_range():
    sat = build_satellite(ISS_TLE)
    pos = get_position(sat)
    assert -90 <= pos["lat"] <= 90, f"Latitude out of range: {pos['lat']}"
    assert -180 <= pos["lon"] <= 180, f"Longitude out of range: {pos['lon']}"

def test_get_position_altitude_positive():
    sat = build_satellite(ISS_TLE)
    pos = get_position(sat)
    assert pos["alt_km"] > 0, f"Altitude should be positive, got {pos['alt_km']}"

def test_iss_altitude_reasonable():
    sat = build_satellite(ISS_TLE)
    pos = get_position(sat)
    assert 200 < pos["alt_km"] < 600, f"ISS altitude should be ~400km, got {pos['alt_km']}"

def test_iss_speed_reasonable():
    sat = build_satellite(ISS_TLE)
    pos = get_position(sat)
    assert 6.0 < pos["speed_kms"] < 9.0, f"ISS speed should be ~7.7 km/s, got {pos['speed_kms']}"

def test_hubble_altitude_reasonable():
    sat = build_satellite(HUBBLE_TLE)
    pos = get_position(sat)
    assert 400 < pos["alt_km"] < 700, f"Hubble altitude should be ~535km, got {pos['alt_km']}"

def test_get_positions_bulk_count():
    results = get_positions_bulk([ISS_TLE, HUBBLE_TLE])
    assert len(results) == 2

def test_get_positions_bulk_no_errors():
    results = get_positions_bulk([ISS_TLE, HUBBLE_TLE])
    for r in results:
        assert "error" not in r, f"Unexpected error for {r.get('name')}: {r.get('error')}"

def test_get_positions_bulk_bad_tle():
    bad = {"name": "GARBAGE", "line1": "bad", "line2": "data"}
    results = get_positions_bulk([ISS_TLE, bad])
    assert results[0]["name"] == "ISS (ZARYA)"
    assert "error" in results[1]

def test_pass_window_returns_list():
    sat = build_satellite(ISS_TLE)
    # Kathmandu
    passes = get_pass_window(sat, observer_lat=27.7172, observer_lon=85.3240)
    assert isinstance(passes, list)

def test_pass_window_fields():
    sat = build_satellite(ISS_TLE)
    passes = get_pass_window(sat, observer_lat=27.7172, observer_lon=85.3240, hours=48)
    for p in passes:
        assert "rise_time" in p
        assert "set_time" in p
        assert "max_elevation_deg" in p
        assert p["max_elevation_deg"] >= 10.0


# ── Run summary ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    tests = [v for k, v in list(globals().items()) if k.startswith("test_")]
    passed = failed = 0
    for t in tests:
        try:
            t()
            print(f"  ✓  {t.__name__}")
            passed += 1
        except Exception as e:
            print(f"  ✗  {t.__name__}: {e}")
            failed += 1
    print(f"\n{passed} passed, {failed} failed")
