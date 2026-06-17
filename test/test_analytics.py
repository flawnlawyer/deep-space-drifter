"""
tests/test_analytics.py
Tests for core/analytics.py using a simulated dataset that mimics real
orbital behavior: per-orbit eccentricity oscillation superimposed on a
slow secular decay trend, plus a synthetic maneuver (sudden raise).
"""

import sys
import math
import tempfile
from pathlib import Path
from datetime import datetime, timedelta, timezone

sys.path.insert(0, str(Path(__file__).parent.parent))

import core.storage as storage_module


def _use_temp_db():
    tmpdir = tempfile.mkdtemp()
    storage_module.DB_PATH = Path(tmpdir) / "test_analytics.db"
    storage_module.init_db()


def _generate_orbit_history(
    name: str,
    n_samples: int,
    interval_minutes: float,
    base_alt_km: float,
    eccentricity_amplitude_km: float,
    orbital_period_min: float,
    decay_km_per_day: float,
    start_time: datetime = None,
):
    """
    Generate a synthetic position history:
    altitude(t) = base_alt - decay_rate * t_days + ecc_amplitude * sin(2*pi*t / period)
    """
    if start_time is None:
        start_time = datetime(2026, 6, 1, tzinfo=timezone.utc)

    rows = []
    for i in range(n_samples):
        t_minutes = i * interval_minutes
        t_days = t_minutes / 1440.0
        phase = 2 * math.pi * (t_minutes / orbital_period_min)

        alt = (
            base_alt_km
            - decay_km_per_day * t_days
            + eccentricity_amplitude_km * math.sin(phase)
        )
        epoch_dt = start_time + timedelta(minutes=t_minutes)
        epoch = epoch_dt.strftime("%Y-%m-%dT%H:%M:%SZ")

        rows.append({
            "name": name,
            "lat": 0.0,
            "lon": 0.0,
            "alt_km": round(alt, 4),
            "speed_kms": 7.66,
            "epoch": epoch,
        })

    return rows


# ── get_decay_rate ─────────────────────────────────────────────────────────────

def test_decay_rate_none_with_one_sample():
    from core import analytics
    _use_temp_db()
    storage_module.save_positions([
        {"name": "SAT1", "lat": 0, "lon": 0, "alt_km": 400, "speed_kms": 7.6, "epoch": "2026-06-01T00:00:00Z"}
    ])
    assert analytics.get_decay_rate("SAT1") is None


def test_decay_rate_unreliable_short_window():
    """Short windows (<6h default) should be flagged unreliable with decay=None."""
    from core import analytics
    _use_temp_db()
    rows = _generate_orbit_history(
        "SAT2", n_samples=10, interval_minutes=1,
        base_alt_km=420, eccentricity_amplitude_km=2.0,
        orbital_period_min=93, decay_km_per_day=0.1,
    )
    storage_module.save_positions(rows)
    rate = analytics.get_decay_rate("SAT2")
    assert rate is not None
    assert rate["reliable"] is False
    assert rate["decay_km_per_day"] is None
    assert rate["span_minutes"] < 360


def test_decay_rate_reliable_long_window_recovers_true_rate():
    """
    With >6h of data spanning many orbits, the orbit-averaging approach
    should recover something close to the true injected decay rate,
    despite large eccentricity oscillation.
    """
    from core import analytics
    _use_temp_db()
    true_decay = 2.0  # km/day — exaggerated vs real ISS but good for signal/noise check
    rows = _generate_orbit_history(
        "SAT3", n_samples=200, interval_minutes=5,  # 1000 min = ~16.7h, ~10.7 orbits
        base_alt_km=420, eccentricity_amplitude_km=3.0,
        orbital_period_min=93, decay_km_per_day=true_decay,
    )
    storage_module.save_positions(rows)
    rate = analytics.get_decay_rate("SAT3")

    assert rate is not None
    assert rate["reliable"] is True
    assert rate["decay_km_per_day"] is not None
    # Should recover a negative decay rate roughly on the order of the true rate
    assert rate["decay_km_per_day"] < 0, "Decay should be negative (altitude decreasing)"
    # Allow generous tolerance given averaging method + eccentricity noise
    assert abs(rate["decay_km_per_day"] - (-true_decay)) < 1.0, \
        f"Expected approx -{true_decay} km/day, got {rate['decay_km_per_day']}"


def test_decay_rate_zero_decay_near_zero_result():
    """A satellite with pure eccentricity oscillation and no decay should
    produce a decay rate close to zero over a long window."""
    from core import analytics
    _use_temp_db()
    rows = _generate_orbit_history(
        "SAT_STABLE", n_samples=200, interval_minutes=5,
        base_alt_km=550, eccentricity_amplitude_km=2.0,
        orbital_period_min=95, decay_km_per_day=0.0,
    )
    storage_module.save_positions(rows)
    rate = analytics.get_decay_rate("SAT_STABLE")

    assert rate is not None
    assert rate["reliable"] is True
    assert abs(rate["decay_km_per_day"]) < 0.5, \
        f"Expected ~0 km/day for non-decaying orbit, got {rate['decay_km_per_day']}"


def test_orbital_period_estimate_reasonable():
    from core import analytics
    _use_temp_db()
    rows = _generate_orbit_history(
        "SAT4", n_samples=200, interval_minutes=5,
        base_alt_km=420, eccentricity_amplitude_km=2.0,
        orbital_period_min=93, decay_km_per_day=0.1,
    )
    storage_module.save_positions(rows)
    rate = analytics.get_decay_rate("SAT4")
    # at ~420km altitude and 7.66 km/s, orbital period should be roughly 90-95 min
    assert 85 < rate["orbital_period_min"] < 100


# ── get_all_decay_rates ──────────────────────────────────────────────────────

def test_get_all_decay_rates_multiple_satellites():
    from core import analytics
    _use_temp_db()
    for sat_name, decay in [("FAST_DECAY", 5.0), ("SLOW_DECAY", 0.5)]:
        rows = _generate_orbit_history(
            sat_name, n_samples=200, interval_minutes=5,
            base_alt_km=400, eccentricity_amplitude_km=2.0,
            orbital_period_min=92, decay_km_per_day=decay,
        )
        storage_module.save_positions(rows)

    results = analytics.get_all_decay_rates()
    assert len(results) == 2
    # fastest decay (most negative) should sort first
    assert results[0]["name"] == "FAST_DECAY"
    assert results[0]["decay_km_per_day"] < results[1]["decay_km_per_day"]


def test_get_all_decay_rates_empty_db():
    from core import analytics
    _use_temp_db()
    assert analytics.get_all_decay_rates() == []


# ── detect_altitude_anomalies ────────────────────────────────────────────────

def test_anomaly_detection_no_false_positives_on_pure_oscillation():
    """Normal eccentricity oscillation alone should NOT trigger anomalies
    at the default 2km threshold against local moving average."""
    from core import analytics
    _use_temp_db()
    rows = _generate_orbit_history(
        "SAT_NORMAL", n_samples=100, interval_minutes=5,
        base_alt_km=420, eccentricity_amplitude_km=3.0,
        orbital_period_min=93, decay_km_per_day=0.1,
    )
    storage_module.save_positions(rows)
    anomalies = analytics.detect_altitude_anomalies("SAT_NORMAL")
    assert anomalies == [], f"Expected no anomalies from pure oscillation, got {len(anomalies)}"


def test_anomaly_detection_catches_injected_maneuver():
    """Inject a sudden +10km altitude jump (simulated orbit raise) partway
    through and confirm it gets flagged."""
    from core import analytics
    _use_temp_db()
    rows = _generate_orbit_history(
        "SAT_MANEUVER", n_samples=100, interval_minutes=5,
        base_alt_km=420, eccentricity_amplitude_km=2.0,
        orbital_period_min=93, decay_km_per_day=0.1,
    )
    # inject a maneuver: bump altitude by +15km for the second half
    for row in rows[50:]:
        row["alt_km"] += 15.0

    storage_module.save_positions(rows)
    anomalies = analytics.detect_altitude_anomalies("SAT_MANEUVER", threshold_km=2.0)
    assert len(anomalies) > 0, "Expected the injected maneuver to be flagged"
    # the flagged points should be near the transition (index ~50)
    assert any(a["direction"] == "raise" for a in anomalies)


def test_anomaly_detection_insufficient_samples():
    from core import analytics
    _use_temp_db()
    rows = _generate_orbit_history(
        "SAT_SHORT", n_samples=5, interval_minutes=5,
        base_alt_km=420, eccentricity_amplitude_km=2.0,
        orbital_period_min=93, decay_km_per_day=0.1,
    )
    storage_module.save_positions(rows)
    assert analytics.detect_altitude_anomalies("SAT_SHORT") == []


# ── correlate_decay_with_kp ───────────────────────────────────────────────────

def test_correlate_decay_with_kp_no_weather_data():
    from core import analytics
    _use_temp_db()
    rows = _generate_orbit_history(
        "SAT5", n_samples=200, interval_minutes=5,
        base_alt_km=420, eccentricity_amplitude_km=2.0,
        orbital_period_min=93, decay_km_per_day=1.0,
    )
    storage_module.save_positions(rows)
    corr = analytics.correlate_decay_with_kp("SAT5")
    assert corr is not None
    assert corr["avg_kp"] is None  # no weather data logged
    assert corr["kp_samples"] == 0


def test_correlate_decay_with_kp_with_matching_weather():
    from core import analytics
    _use_temp_db()
    rows = _generate_orbit_history(
        "SAT6", n_samples=200, interval_minutes=5,
        base_alt_km=420, eccentricity_amplitude_km=2.0,
        orbital_period_min=93, decay_km_per_day=1.0,
        start_time=datetime(2026, 6, 1, 0, 0, tzinfo=timezone.utc),
    )
    storage_module.save_positions(rows)

    # Add Kp readings within the window (2026-06-01 00:00 to ~16:40)
    weather_points = [
        {"metric": "kp", "value": 3.0, "time_tag": "2026-06-01T03:00:00", "source": "noaa_kp_forecast", "status": "observed"},
        {"metric": "kp", "value": 5.0, "time_tag": "2026-06-01T09:00:00", "source": "noaa_kp_forecast", "status": "estimated"},
        {"metric": "kp", "value": 9.0, "time_tag": "2026-06-02T00:00:00", "source": "noaa_kp_forecast", "status": "predicted"},  # outside window, predicted -> excluded
    ]
    storage_module.save_weather_points(weather_points)

    corr = analytics.correlate_decay_with_kp("SAT6")
    assert corr is not None
    assert corr["kp_samples"] == 2
    assert corr["avg_kp"] == 4.0  # (3.0 + 5.0) / 2


def test_correlate_decay_with_kp_unreliable_decay_still_returns():
    """Even if decay is unreliable (short window), correlation should still
    return a dict with decay_km_per_day=None rather than crashing."""
    from core import analytics
    _use_temp_db()
    rows = _generate_orbit_history(
        "SAT7", n_samples=5, interval_minutes=5,
        base_alt_km=420, eccentricity_amplitude_km=2.0,
        orbital_period_min=93, decay_km_per_day=1.0,
    )
    storage_module.save_positions(rows)
    corr = analytics.correlate_decay_with_kp("SAT7")
    assert corr is not None
    assert corr["reliable"] is False
    assert corr["decay_km_per_day"] is None


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
