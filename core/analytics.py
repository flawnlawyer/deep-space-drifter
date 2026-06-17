"""
deep-space-drifter / core / analytics.py
Derive intelligence from stored position and space weather history:
- altitude decay rate per satellite
- decay rate vs Kp index correlation
- simple anomaly flags (sudden altitude/speed jumps = maneuvers)

IMPORTANT — why this is harder than "subtract two altitudes":
A satellite's instantaneous altitude oscillates every orbit due to
eccentricity (perigee/apogee), even with zero atmospheric decay. The ISS,
for example, swings several km between perigee and apogee on a ~93min orbit.
Comparing two raw altitude samples — even an hour apart — mostly measures
WHERE IN THE ORBIT each sample landed, not true secular decay.

True decay needs either:
  (a) averaging altitude over >= 1 full orbit (multiple full periods, ideally
      many), or
  (b) reading the decay signal directly from consecutive TLEs' mean motion
      (n) and its rate of change (n_dot) — this is what professional
      tracking actually uses.

This module implements (a) as a rough v0.3 signal — it's directionally
useful and good for relative comparisons between satellites, but absolute
km/day figures over short windows (hours) will be noisy. Treat
`reliable=False` results as "not enough data yet" and treat all results as
approximate until the dataset spans multiple days.
"""

from datetime import datetime, timezone
import core.storage


def _parse_epoch(epoch: str) -> datetime:
    """Parse an ISO epoch string into an aware UTC datetime.
    Handles trailing 'Z' and naive timestamps (assumed UTC)."""
    if epoch.endswith("Z"):
        epoch = epoch[:-1] + "+00:00"
    dt = datetime.fromisoformat(epoch)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def get_decay_rate(name: str, limit: int = 1000, min_span_minutes: float = 360.0) -> dict | None:
    """
    Estimate altitude decay rate by comparing orbit-averaged altitudes
    between the first and second half of the available history.

    Averaging over each half smooths out eccentricity-driven oscillation
    (perigee/apogee swings), giving a much more honest decay signal than
    a raw two-point difference.

    `min_span_minutes` defaults to 360 (6 hours) — roughly 4 ISS orbits —
    the minimum needed for averaging to meaningfully cancel oscillation.
    Results with span < min_span_minutes are marked `reliable=False` and
    `decay_km_per_day=None`.

    Returns:
        {
          name, samples, span_minutes, reliable,
          alt_avg_first_half_km, alt_avg_second_half_km, alt_change_km,
          decay_km_per_day, decay_km_per_orbit (approx),
        }
        or None if fewer than 2 samples.
    """
    history = core.storage.get_position_history(name, limit=limit)
    if len(history) < 2:
        return None

    # history is newest-first; reverse to oldest-first
    history = list(reversed(history))

    t0 = _parse_epoch(history[0]["epoch"])
    t1 = _parse_epoch(history[-1]["epoch"])
    span_seconds = (t1 - t0).total_seconds()
    if span_seconds <= 0:
        return None

    span_minutes = span_seconds / 60
    reliable = span_minutes >= min_span_minutes

    mid = len(history) // 2
    first_half = history[:max(mid, 1)]
    second_half = history[max(mid, 1):]

    alt_avg_first = sum(p["alt_km"] for p in first_half) / len(first_half)
    alt_avg_second = sum(p["alt_km"] for p in second_half) / len(second_half)
    alt_change = alt_avg_second - alt_avg_first

    # midpoint-to-midpoint time span for the rate calc
    t_first_mid = _parse_epoch(first_half[len(first_half) // 2]["epoch"])
    t_second_mid = _parse_epoch(second_half[len(second_half) // 2]["epoch"])
    rate_span_days = (t_second_mid - t_first_mid).total_seconds() / 86400.0

    decay_km_per_day = None
    if reliable and rate_span_days > 0:
        decay_km_per_day = alt_change / rate_span_days

    # Approximate orbital period from speed + altitude (circular orbit assumption)
    avg_alt = (alt_avg_first + alt_avg_second) / 2
    avg_speed = sum(p["speed_kms"] for p in history) / len(history)
    earth_radius_km = 6371.0
    orbit_radius_km = earth_radius_km + avg_alt
    orbital_period_s = (2 * 3.14159265 * orbit_radius_km) / avg_speed if avg_speed > 0 else None

    decay_km_per_orbit = None
    if decay_km_per_day is not None and orbital_period_s:
        decay_km_per_orbit = decay_km_per_day * (orbital_period_s / 86400.0)

    return {
        "name": name,
        "samples": len(history),
        "span_minutes": round(span_minutes, 2),
        "reliable": reliable,
        "alt_avg_first_half_km": round(alt_avg_first, 4),
        "alt_avg_second_half_km": round(alt_avg_second, 4),
        "alt_change_km": round(alt_change, 4),
        "decay_km_per_day": round(decay_km_per_day, 4) if decay_km_per_day is not None else None,
        "decay_km_per_orbit": round(decay_km_per_orbit, 6) if decay_km_per_orbit is not None else None,
        "orbital_period_min": round(orbital_period_s / 60, 2) if orbital_period_s else None,
    }


def get_all_decay_rates(limit: int = 1000, min_span_minutes: float = 360.0) -> list[dict]:
    """Compute decay rates for every tracked satellite that has enough history."""
    results = []
    for name in core.storage.get_tracked_satellites():
        rate = get_decay_rate(name, limit=limit, min_span_minutes=min_span_minutes)
        if rate:
            results.append(rate)
    # sort: reliable decay rates first (fastest decay = most negative), unreliable last
    results.sort(key=lambda r: (not r["reliable"], r["decay_km_per_day"] if r["decay_km_per_day"] is not None else 0))
    return results


def detect_altitude_anomalies(name: str, limit: int = 1000, threshold_km: float = 2.0, window: int = 5) -> list[dict]:
    """
    Flag samples whose altitude deviates sharply from the local moving
    average — a signature of a maneuver (orbit raise/deboost burn) rather
    than normal eccentricity-driven oscillation.

    Raw consecutive-sample deltas are NOT used directly: ISS-class orbits
    routinely swing several km between perigee and apogee within a single
    pass, which would otherwise trigger false positives on every sample.

    `window` is the number of samples on each side used for the local
    moving average. `threshold_km` is the deviation from that average
    required to flag a point.

    Returns list of {epoch, alt_km, local_avg_km, deviation_km}.
    """
    history = core.storage.get_position_history(name, limit=limit)
    if len(history) < (window * 2 + 1):
        return []

    history = list(reversed(history))  # oldest-first
    alts = [p["alt_km"] for p in history]

    anomalies = []
    for i in range(window, len(history) - window):
        local = alts[i - window:i] + alts[i + 1:i + window + 1]
        local_avg = sum(local) / len(local)
        deviation = alts[i] - local_avg
        if abs(deviation) >= threshold_km:
            anomalies.append({
                "epoch": history[i]["epoch"],
                "alt_km": alts[i],
                "local_avg_km": round(local_avg, 4),
                "deviation_km": round(deviation, 4),
                "direction": "raise" if deviation > 0 else "deboost/decay",
            })

    return anomalies


def correlate_decay_with_kp(name: str, limit: int = 1000, min_span_minutes: float = 360.0) -> dict | None:
    """
    Compare a satellite's decay rate against the average Kp index
    over the same time window. Higher Kp -> denser thermosphere -> faster decay.

    Returns:
        {name, decay_km_per_day, reliable, avg_kp, kp_samples, window}
        or None if insufficient data.
    """
    decay = get_decay_rate(name, limit=limit, min_span_minutes=min_span_minutes)
    if decay is None:
        return None

    history = core.storage.get_position_history(name, limit=limit)
    if len(history) < 2:
        return None

    history = list(reversed(history))
    t_start = _parse_epoch(history[0]["epoch"])
    t_end = _parse_epoch(history[-1]["epoch"])

    kp_history = core.storage.get_weather_history("kp", limit=500)
    relevant_kp = []
    for point in kp_history:
        try:
            kp_time = _parse_epoch(point["time_tag"])
        except ValueError:
            continue
        if t_start <= kp_time <= t_end and point["status"] in ("observed", "estimated"):
            relevant_kp.append(point["value"])

    if not relevant_kp:
        # fall back to most recent observed/estimated Kp as a rough proxy
        for point in kp_history:
            if point["status"] in ("observed", "estimated"):
                relevant_kp = [point["value"]]
                break

    avg_kp = sum(relevant_kp) / len(relevant_kp) if relevant_kp else None

    return {
        "name": name,
        "decay_km_per_day": decay["decay_km_per_day"],
        "reliable": decay["reliable"],
        "avg_kp": round(avg_kp, 2) if avg_kp is not None else None,
        "kp_samples": len(relevant_kp),
        "window_start": history[0]["epoch"],
        "window_end": history[-1]["epoch"],
    }


if __name__ == "__main__":
    tracked = core.storage.get_tracked_satellites()
    if not tracked:
        print("No satellite history found. Run 'python drifter.py --watch --log' first.")
    else:
        print(f"Analyzing {len(tracked)} tracked satellites...\n")

        rates = get_all_decay_rates()
        if not rates:
            print("Not enough samples yet for any satellite (need >= 2 position snapshots).")
        else:
            print(f"{'Satellite':<28} {'Samples':>8} {'Span(min)':>10} {'Alt change(km)':>15} {'Decay (km/day)':>15}")
            print("-" * 82)
            for r in rates:
                decay_str = f"{r['decay_km_per_day']:.4f}" if r["decay_km_per_day"] is not None else "n/a (<60min)"
                print(f"{r['name']:<28} {r['samples']:>8} {r['span_minutes']:>10} {r['alt_change_km']:>15.4f} {decay_str:>15}")

            short_window = [r for r in rates if not r["reliable"]]
            if short_window:
                print(f"\n  Note: {len(short_window)} satellite(s) have <6h of history.")
                print(f"  Decay rates need a longer window to average out orbital wobble — keep --watch --log running.")

            print("\n--- Anomaly check (altitude deviates >= 2km from local moving average) ---\n")
            any_anomaly = False
            for r in rates:
                anomalies = detect_altitude_anomalies(r["name"])
                if anomalies:
                    any_anomaly = True
                    print(f"  {r['name']}:")
                    for a in anomalies:
                        print(f"    {a['epoch']}: {a['alt_km']:.1f} km vs local avg {a['local_avg_km']:.1f} km "
                              f"({a['deviation_km']:+.4f} km, {a['direction']})")
            if not any_anomaly:
                print("  No anomalies detected (or not enough samples — need >= 11 per satellite).")

            print("\n--- Decay vs Kp correlation (ISS, if tracked) ---\n")
            iss = next((n for n in tracked if "ISS" in n.upper() and "ZARYA" in n.upper()), None)
            if iss:
                corr = correlate_decay_with_kp(iss)
                if corr:
                    decay_str = f"{corr['decay_km_per_day']:.4f} km/day" if corr["decay_km_per_day"] is not None else "n/a (need >=6h history)"
                    kp_str = f"{corr['avg_kp']}" if corr["avg_kp"] is not None else "n/a"
                    print(f"  {corr['name']}")
                    print(f"  Decay rate:  {decay_str}")
                    print(f"  Avg Kp:      {kp_str} (from {corr['kp_samples']} samples)")
                    print(f"  Window:      {corr['window_start']} -> {corr['window_end']}")
            else:
                print("  ISS not in tracked satellites.")
