"""
deep-space-drifter / core / propagate.py
Compute satellite positions from TLE data using Skyfield (SGP4).
"""

from datetime import datetime, timezone
from skyfield.api import EarthSatellite, load, wgs84


ts = load.timescale()


def build_satellite(tle: dict) -> EarthSatellite:
    """Wrap a TLE dict into a Skyfield EarthSatellite object."""
    line1, line2 = tle["line1"], tle["line2"]
    if not (line1.startswith("1 ") and len(line1) >= 69):
        raise ValueError(f"Invalid TLE line 1: {line1!r}")
    if not (line2.startswith("2 ") and len(line2) >= 69):
        raise ValueError(f"Invalid TLE line 2: {line2!r}")
    return EarthSatellite(line1, line2, tle["name"], ts)


def get_position(sat: EarthSatellite, at: datetime | None = None) -> dict:
    """
    Compute the geographic position of a satellite.
    Returns lat (deg), lon (deg), altitude (km), speed (km/s).
    Defaults to now if no time given.
    """
    if at is None:
        t = ts.now()
    else:
        t = ts.from_datetime(at.replace(tzinfo=timezone.utc))

    geocentric = sat.at(t)
    subpoint   = wgs84.subpoint(geocentric)
    velocity   = geocentric.velocity.km_per_s
    speed      = sum(v**2 for v in velocity) ** 0.5

    return {
        "name":      sat.name,
        "lat":       round(subpoint.latitude.degrees,  4),
        "lon":       round(subpoint.longitude.degrees, 4),
        "alt_km":    round(subpoint.elevation.km,      2),
        "speed_kms": round(speed, 3),
        "epoch":     t.utc_iso(),
    }


def get_positions_bulk(tles: list[dict], at: datetime | None = None) -> list[dict]:
    """Compute positions for a list of TLE dicts in one pass."""
    results = []
    for tle in tles:
        try:
            sat = build_satellite(tle)
            pos = get_position(sat, at)
            results.append(pos)
        except Exception as e:
            results.append({
                "name":  tle.get("name", "unknown"),
                "error": str(e),
            })
    return results


def get_pass_window(
    sat: EarthSatellite,
    observer_lat: float,
    observer_lon: float,
    observer_elev_m: float = 1400,
    hours: int = 24,
) -> list[dict]:
    """
    Find upcoming visible passes over an observer location.
    Default observer is Kathmandu (lat=27.7, lon=85.3, elev=1400m).
    Returns list of {rise_time, culmination_time, set_time, max_elevation_deg}.
    """
    from skyfield.api import Topos

    observer = wgs84.latlon(observer_lat, observer_lon, observer_elev_m)
    t0 = ts.now()
    t1 = ts.tt_jd(t0.tt + hours / 24.0)

    times, events = sat.find_events(observer, t0, t1, altitude_degrees=10.0)

    passes = []
    current = {}

    for ti, event in zip(times, events):
        if event == 0:
            current = {"rise_time": ti.utc_iso()}
        elif event == 1:
            alt, az, dist = (sat - observer).at(ti).altaz()
            current["max_elevation_deg"] = round(alt.degrees, 1)
            current["culmination_time"]  = ti.utc_iso()
        elif event == 2:
            current["set_time"] = ti.utc_iso()
            passes.append(current)
            current = {}

    return passes


if __name__ == "__main__":
    import sys
    sys.path.insert(0, str(__import__("pathlib").Path(__file__).parent.parent))
    from core.fetch import get_satellites

    print("Fetching TLE data...")
    sats_raw = get_satellites("stations_tle")

    print(f"\nCurrent positions ({len(sats_raw)} satellites):\n")
    print(f"{'Name':<30} {'Lat':>8} {'Lon':>9} {'Alt (km)':>10} {'Speed (km/s)':>13}")
    print("-" * 75)

    positions = get_positions_bulk(sats_raw)
    for p in positions:
        if "error" not in p:
            print(f"{p['name']:<30} {p['lat']:>8.2f} {p['lon']:>9.2f} {p['alt_km']:>10.1f} {p['speed_kms']:>13.3f}")
        else:
            print(f"{p['name']:<30}  ERROR: {p['error']}")

    print(f"\n{'='*75}")
    print(f"Epoch: {positions[0]['epoch'] if positions else 'n/a'}")

    print(f"\n--- Pass predictions over Kathmandu (next 24h) ---\n")
    if sats_raw:
        iss_tle = next((s for s in sats_raw if "ISS" in s["name"].upper()), sats_raw[0])
        iss = build_satellite(iss_tle)
        passes = get_pass_window(iss, observer_lat=27.7172, observer_lon=85.3240)
        if passes:
            for p in passes:
                print(f"  Rise:   {p.get('rise_time', '?')}")
                print(f"  Peak:   {p.get('max_elevation_deg', '?')}° at {p.get('culmination_time', '?')}")
                print(f"  Set:    {p.get('set_time', '?')}")
                print()
        else:
            print("  No passes above 10° in the next 24 hours.")
