"""
tests/test_storage_weather.py
Tests for core/storage.py and core/spaceweather.py (parsing logic, no network).
Run: python -m pytest tests/ -v
"""

import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import core.storage as storage_module
from core import spaceweather


# ── Fixtures: redirect storage to a temp DB for test isolation ───────────────

def _use_temp_db():
    tmpdir = tempfile.mkdtemp()
    storage_module.DB_PATH = Path(tmpdir) / "test_drifter.db"
    storage_module.init_db()


SAMPLE_POSITIONS = [
    {"name": "ISS (ZARYA)", "lat": 11.44, "lon": -167.12, "alt_km": 422.2, "speed_kms": 7.658, "epoch": "2026-06-13T15:27:50Z"},
    {"name": "CSS (TIANHE)", "lat": -19.29, "lon": -173.55, "alt_km": 388.6, "speed_kms": 7.678, "epoch": "2026-06-13T15:27:50Z"},
    {"name": "BAD SAT", "error": "propagation failed"},
]

SAMPLE_WEATHER = [
    {"metric": "kp", "value": 4.0, "time_tag": "2026-06-13T12:00:00", "source": "noaa_kp_forecast", "status": "observed"},
    {"metric": "kp", "value": 5.67, "time_tag": "2026-06-13T15:00:00", "source": "noaa_kp_forecast", "status": "predicted"},
    {"metric": "speed", "value": 512.3, "time_tag": "2026-06-13 15:20:00.000", "source": "noaa_plasma_1day"},
]

# Real NOAA Kp forecast response shape
SAMPLE_KP_RAW = [
    {"time_tag": "2026-06-13T12:00:00", "kp": 4.00, "observed": "observed", "noaa_scale": None},
    {"time_tag": "2026-06-13T15:00:00", "kp": 5.67, "observed": "estimated", "noaa_scale": "G2"},
    {"time_tag": "2026-06-13T18:00:00", "kp": 6.00, "observed": "predicted", "noaa_scale": "G2"},
    {"time_tag": "2026-06-13T21:00:00", "kp": 7.33, "observed": "predicted", "noaa_scale": "G3"},
]

# Real NOAA plasma response shape (array-of-arrays with header)
SAMPLE_PLASMA_RAW = [
    ["time_tag", "density", "speed", "temperature"],
    ["2026-06-13 15:20:00.000", "3.30", "522.3", "324410"],
    ["2026-06-13 15:21:00.000", "2.95", "508.9", "323745"],
    ["2026-06-13 15:22:00.000", None, "510.0", "320000"],  # null density
]


# ── Storage: positions ────────────────────────────────────────────────────────

def test_save_positions_skips_errors():
    _use_temp_db()
    n = storage_module.save_positions(SAMPLE_POSITIONS)
    assert n == 2, f"Expected 2 saved (skipping the error entry), got {n}"

def test_save_positions_empty_list():
    _use_temp_db()
    n = storage_module.save_positions([])
    assert n == 0

def test_get_position_history_returns_data():
    _use_temp_db()
    storage_module.save_positions(SAMPLE_POSITIONS)
    history = storage_module.get_position_history("ISS (ZARYA)")
    assert len(history) == 1
    assert history[0]["lat"] == 11.44
    assert history[0]["alt_km"] == 422.2

def test_get_position_history_missing_satellite():
    _use_temp_db()
    storage_module.save_positions(SAMPLE_POSITIONS)
    history = storage_module.get_position_history("NONEXISTENT SAT")
    assert history == []

def test_get_tracked_satellites():
    _use_temp_db()
    storage_module.save_positions(SAMPLE_POSITIONS)
    tracked = storage_module.get_tracked_satellites()
    assert "ISS (ZARYA)" in tracked
    assert "CSS (TIANHE)" in tracked
    assert "BAD SAT" not in tracked  # error entry never saved

def test_count_positions():
    _use_temp_db()
    storage_module.save_positions(SAMPLE_POSITIONS)
    assert storage_module.count_positions() == 2

def test_position_history_accumulates_over_multiple_saves():
    _use_temp_db()
    storage_module.save_positions(SAMPLE_POSITIONS)
    # simulate a second snapshot a bit later
    second = [
        {"name": "ISS (ZARYA)", "lat": 12.0, "lon": -166.0, "alt_km": 421.0, "speed_kms": 7.66, "epoch": "2026-06-13T15:29:50Z"},
    ]
    storage_module.save_positions(second)
    history = storage_module.get_position_history("ISS (ZARYA)")
    assert len(history) == 2
    # newest first
    assert history[0]["epoch"] == "2026-06-13T15:29:50Z"


# ── Storage: space weather ─────────────────────────────────────────────────────

def test_save_weather_points():
    _use_temp_db()
    n = storage_module.save_weather_points(SAMPLE_WEATHER)
    assert n == 3

def test_save_weather_points_dedupes():
    _use_temp_db()
    storage_module.save_weather_points(SAMPLE_WEATHER)
    n2 = storage_module.save_weather_points(SAMPLE_WEATHER)
    assert n2 == 0, "Duplicate (metric, time_tag, source) should be ignored"

def test_get_latest_weather():
    _use_temp_db()
    storage_module.save_weather_points(SAMPLE_WEATHER)
    latest = storage_module.get_latest_weather("kp")
    assert latest is not None
    assert latest["time_tag"] == "2026-06-13T15:00:00"
    assert latest["value"] == 5.67

def test_get_latest_weather_missing_metric():
    _use_temp_db()
    storage_module.save_weather_points(SAMPLE_WEATHER)
    result = storage_module.get_latest_weather("nonexistent_metric")
    assert result is None

def test_get_weather_history():
    _use_temp_db()
    storage_module.save_weather_points(SAMPLE_WEATHER)
    history = storage_module.get_weather_history("kp")
    assert len(history) == 2
    assert history[0]["time_tag"] == "2026-06-13T15:00:00"  # newest first

def test_count_weather_points():
    _use_temp_db()
    storage_module.save_weather_points(SAMPLE_WEATHER)
    assert storage_module.count_weather_points() == 3


# ── Space weather parsing (no network — using sample raw responses) ──────────

def test_kp_index_parsing_shape():
    points = []
    for entry in SAMPLE_KP_RAW:
        points.append({
            "metric": "kp",
            "value": float(entry["kp"]),
            "time_tag": entry["time_tag"],
            "source": "noaa_kp_forecast",
            "status": entry.get("observed"),
        })
    assert len(points) == 4
    assert points[0]["value"] == 4.0
    assert points[2]["status"] == "predicted"

def test_plasma_parsing_shape():
    header = SAMPLE_PLASMA_RAW[0]
    rows = SAMPLE_PLASMA_RAW[1:]
    points = []
    for row in rows:
        record = dict(zip(header, row))
        time_tag = record.get("time_tag")
        for field in header:
            if field == "time_tag":
                continue
            value = record.get(field)
            if value is None:
                continue
            try:
                value = float(value)
            except (ValueError, TypeError):
                continue
            points.append({"metric": field, "value": value, "time_tag": time_tag, "source": "noaa_plasma_1day"})

    # 2 full rows * 3 fields + 1 row with density=None (2 fields) = 8
    assert len(points) == 8
    densities = [p for p in points if p["metric"] == "density"]
    assert len(densities) == 2  # third row's null density skipped

def test_storm_label_thresholds():
    conditions_fn = spaceweather.KP_SCALE
    assert conditions_fn[5] == "G1 (Minor)"
    assert conditions_fn[9] == "G5 (Extreme)"

def test_get_current_conditions_logic_with_sample_data(monkeypatch):
    monkeypatch.setattr(spaceweather, "fetch_kp_index", lambda: [
        {"metric": "kp", "value": float(e["kp"]), "time_tag": e["time_tag"], "source": "noaa_kp_forecast", "status": e["observed"]}
        for e in SAMPLE_KP_RAW
    ])
    monkeypatch.setattr(spaceweather, "fetch_solar_wind", lambda window="plasma_1day": [
        {"metric": "speed", "value": 522.3, "time_tag": "2026-06-13 15:20:00.000", "source": "noaa_plasma_1day"},
        {"metric": "density", "value": 3.30, "time_tag": "2026-06-13 15:20:00.000", "source": "noaa_plasma_1day"},
    ])

    conditions = spaceweather.get_current_conditions()

    assert conditions["kp_current"] == 5.67  # latest observed/estimated
    assert conditions["kp_status"] == "estimated"
    assert conditions["storm_level"] == "G1 (Minor)"  # int(5.67) = 5 -> G1
    assert conditions["kp_max_predicted"] == 7.33  # G3 predicted point
    assert conditions["solar_wind_speed_kms"] == 522.3
    assert conditions["solar_wind_density_pcm3"] == 3.30


if __name__ == "__main__":
    tests = [v for k, v in list(globals().items()) if k.startswith("test_")]
    passed = failed = 0
    for t in tests:
        try:
            # handle monkeypatch-requiring test manually
            if "monkeypatch" in t.__code__.co_varnames[:t.__code__.co_argcount]:
                class _MP:
                    def setattr(self, obj, name, value):
                        setattr(obj, name, value)
                t(_MP())
            else:
                t()
            print(f"  ✓  {t.__name__}")
            passed += 1
        except Exception as e:
            print(f"  ✗  {t.__name__}: {e}")
            failed += 1
    print(f"\n{passed} passed, {failed} failed")
