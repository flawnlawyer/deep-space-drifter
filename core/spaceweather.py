"""
deep-space-drifter / core / spaceweather.py
Fetch space weather data from NOAA's Space Weather Prediction Center (SWPC).
No API key required — public JSON endpoints.
"""

import requests

SWPC_BASE = "https://services.swpc.noaa.gov"

ENDPOINTS = {
    "kp_forecast":  f"{SWPC_BASE}/products/noaa-planetary-k-index-forecast.json",
    "plasma_1day":  f"{SWPC_BASE}/products/solar-wind/plasma-1-day.json",
    "mag_1day":     f"{SWPC_BASE}/products/solar-wind/mag-1-day.json",
}

HEADERS = {"User-Agent": "Mozilla/5.0 (DeepSpaceDrifter/0.2; +https://github.com/flawnlawyer/deep-space-drifter)"}

# Kp index thresholds → NOAA G-scale storm category
KP_SCALE = {
    5: "G1 (Minor)",
    6: "G2 (Moderate)",
    7: "G3 (Strong)",
    8: "G4 (Severe)",
    9: "G5 (Extreme)",
}


def _get_json(url: str) -> list:
    resp = requests.get(url, headers=HEADERS, timeout=15)
    resp.raise_for_status()
    return resp.json()


def fetch_kp_index() -> list[dict]:
    """
    Fetch planetary Kp index (observed + forecast).
    Returns list of {metric, value, time_tag, source, status}.
    """
    data = _get_json(ENDPOINTS["kp_forecast"])

    points = []
    for entry in data:
        points.append({
            "metric":   "kp",
            "value":    float(entry["kp"]),
            "time_tag": entry["time_tag"],
            "source":   "noaa_kp_forecast",
            "status":   entry.get("observed"),  # observed | estimated | predicted
        })
    return points


def fetch_solar_wind(window: str = "plasma_1day") -> list[dict]:
    """
    Fetch solar wind plasma data (density, speed, temperature).
    Returns list of {metric, value, time_tag, source} for each measured field.
    """
    if window not in ("plasma_1day", "mag_1day"):
        raise ValueError("window must be 'plasma_1day' or 'mag_1day'")

    data = _get_json(ENDPOINTS[window])
    if len(data) < 2:
        return []

    header = data[0]
    rows = data[1:]
    source = f"noaa_{window}"

    points = []
    for row in rows:
        record = dict(zip(header, row))
        time_tag = record.get("time_tag")
        if not time_tag:
            continue

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

            points.append({
                "metric":   field,          # 'density', 'speed', 'temperature', 'bx_gsm', etc.
                "value":    value,
                "time_tag": time_tag,
                "source":   source,
            })

    return points


def get_current_conditions() -> dict:
    """
    High-level summary: current Kp, latest solar wind speed/density,
    and a human-readable storm status.
    """
    kp_points = fetch_kp_index()
    plasma_points = fetch_solar_wind("plasma_1day")

    # Most recent observed/estimated Kp (skip pure predictions for "current")
    current_kp = None
    for p in reversed(kp_points):
        if p["status"] in ("observed", "estimated"):
            current_kp = p
            break
    if current_kp is None and kp_points:
        current_kp = kp_points[-1]

    # Next predicted peak Kp (for heads-up on incoming storms)
    predicted = [p for p in kp_points if p["status"] == "predicted"]
    max_predicted = max(predicted, key=lambda p: p["value"]) if predicted else None

    # Latest solar wind speed / density
    speeds = [p for p in plasma_points if p["metric"] == "speed"]
    densities = [p for p in plasma_points if p["metric"] == "density"]
    latest_speed = speeds[-1] if speeds else None
    latest_density = densities[-1] if densities else None

    def storm_label(kp_value: float) -> str:
        kp_int = int(kp_value)
        for threshold in sorted(KP_SCALE.keys(), reverse=True):
            if kp_int >= threshold:
                return KP_SCALE[threshold]
        return "Quiet"

    return {
        "kp_current":       current_kp["value"] if current_kp else None,
        "kp_status":        current_kp["status"] if current_kp else None,
        "kp_time":          current_kp["time_tag"] if current_kp else None,
        "storm_level":      storm_label(current_kp["value"]) if current_kp else "Unknown",
        "kp_max_predicted": max_predicted["value"] if max_predicted else None,
        "kp_max_time":      max_predicted["time_tag"] if max_predicted else None,
        "solar_wind_speed_kms":   latest_speed["value"] if latest_speed else None,
        "solar_wind_density_pcm3": latest_density["value"] if latest_density else None,
        "solar_wind_time":  latest_speed["time_tag"] if latest_speed else None,
    }


if __name__ == "__main__":
    print("Fetching space weather from NOAA SWPC...\n")
    conditions = get_current_conditions()

    print("=" * 50)
    print("  Current Space Weather")
    print("=" * 50)
    print(f"  Kp index:        {conditions['kp_current']} ({conditions['kp_status']})")
    print(f"  Storm level:     {conditions['storm_level']}")
    print(f"  Time:            {conditions['kp_time']}")
    print()
    print(f"  Solar wind speed:   {conditions['solar_wind_speed_kms']} km/s")
    print(f"  Solar wind density: {conditions['solar_wind_density_pcm3']} p/cm³")
    print(f"  Measured at:        {conditions['solar_wind_time']}")
    print()
    if conditions["kp_max_predicted"]:
        print(f"  Next 24-72h peak Kp forecast: {conditions['kp_max_predicted']} at {conditions['kp_max_time']}")
    print("=" * 50)
