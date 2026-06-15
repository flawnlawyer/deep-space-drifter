"""
deep-space-drifter / api.py
Flask JSON API — the data layer that the CesiumJS frontend will consume.

Endpoints:
  GET /api/satellites/live?group=stations_tle    current positions
  GET /api/satellites/history/<name>?limit=50   position history
  GET /api/satellites/tracked                    list of tracked sats
  GET /api/satellites/passes/<name>?lat=&lon=&hours=  pass predictions

  GET /api/weather/current                       latest Kp + solar wind
  GET /api/weather/history/<metric>?limit=100    weather time series

  GET /api/analyze/decay                         decay rates all sats
  GET /api/analyze/anomalies/<name>?threshold=2  anomaly scan
  GET /api/analyze/correlate/<name>              decay vs Kp

  GET /api/status                                platform health check

Run:
  python api.py            (dev, port 5000)
  python api.py --port 8080
"""

import argparse
from pathlib import Path
from flask import Flask, jsonify, request, send_from_directory
from core.fetch import get_satellites
from core.propagate import build_satellite, get_positions_bulk, get_pass_window
from core import storage, spaceweather, analytics

app = Flask(__name__)
WEB_DIR = Path(__file__).parent / "web"


@app.after_request
def add_cors(response):
    """Allow the frontend (opened as file://) to call the API."""
    response.headers["Access-Control-Allow-Origin"] = "*"
    return response


@app.route("/ui")
@app.route("/ui/")
def serve_ui():
    return send_from_directory(WEB_DIR, "index.html")


def _err(msg: str, code: int = 400):
    return jsonify({"error": msg}), code


def _ok(data):
    return jsonify({"ok": True, "data": data})


# ── Satellites ────────────────────────────────────────────────────────────────

@app.route("/api/satellites/live")
def satellites_live():
    group = request.args.get("group", "stations_tle")
    refresh = request.args.get("refresh", "false").lower() == "true"
    try:
        tles = get_satellites(group, force_refresh=refresh)
    except Exception as e:
        return _err(str(e))

    positions = get_positions_bulk(tles)
    return _ok({
        "group": group,
        "count": len(positions),
        "positions": positions,
    })


@app.route("/api/satellites/tracked")
def satellites_tracked():
    return _ok({"satellites": storage.get_tracked_satellites()})


@app.route("/api/satellites/history/<path:name>")
def satellite_history(name: str):
    limit = int(request.args.get("limit", 100))
    history = storage.get_position_history(name, limit=limit)
    if not history:
        return _err(f"No history for '{name}'. Log some data first.", 404)
    return _ok({"name": name, "count": len(history), "history": history})


@app.route("/api/satellites/passes/<path:name>")
def satellite_passes(name: str):
    lat   = float(request.args.get("lat",   27.7172))
    lon   = float(request.args.get("lon",   85.3240))
    elev  = float(request.args.get("elev",  1400))
    hours = int(request.args.get("hours",   24))
    group = request.args.get("group", "stations_tle")

    tles = get_satellites(group)
    match = next((t for t in tles if name.upper() in t["name"].upper()), None)
    if not match:
        return _err(f"Satellite '{name}' not found in group '{group}'.", 404)

    sat = build_satellite(match)
    passes = get_pass_window(sat, observer_lat=lat, observer_lon=lon,
                             observer_elev_m=elev, hours=hours)
    return _ok({
        "name": match["name"],
        "observer": {"lat": lat, "lon": lon, "elev_m": elev},
        "hours_ahead": hours,
        "passes": passes,
    })


# ── Space weather ─────────────────────────────────────────────────────────────

@app.route("/api/weather/current")
def weather_current():
    try:
        conditions = spaceweather.get_current_conditions()
    except Exception as e:
        return _err(f"NOAA fetch failed: {e}", 503)
    return _ok(conditions)


@app.route("/api/weather/history/<metric>")
def weather_history(metric: str):
    limit = int(request.args.get("limit", 100))
    history = storage.get_weather_history(metric, limit=limit)
    return _ok({"metric": metric, "count": len(history), "history": history})


# ── Analytics ─────────────────────────────────────────────────────────────────

@app.route("/api/analyze/decay")
def analyze_decay():
    rates = analytics.get_all_decay_rates()
    return _ok({"count": len(rates), "rates": rates})


@app.route("/api/analyze/anomalies/<path:name>")
def analyze_anomalies(name: str):
    threshold = float(request.args.get("threshold", 2.0))
    hits = analytics.detect_altitude_anomalies(name, threshold_km=threshold)
    return _ok({"name": name, "threshold_km": threshold,
                "count": len(hits), "anomalies": hits})


@app.route("/api/analyze/correlate/<path:name>")
def analyze_correlate(name: str):
    corr = analytics.correlate_decay_with_kp(name)
    if corr is None:
        return _err(f"No data for '{name}' or insufficient history.", 404)
    return _ok(corr)


# ── Status ────────────────────────────────────────────────────────────────────

@app.route("/api/status")
def status():
    return _ok({
        "version": "0.3.0",
        "db_path": str(storage.DB_PATH),
        "positions_stored": storage.count_positions(),
        "weather_points_stored": storage.count_weather_points(),
        "tracked_satellites": len(storage.get_tracked_satellites()),
    })


@app.route("/")
def index():
    return jsonify({
        "name": "Deep Space Drifter API",
        "version": "0.3.0",
        "ui": "http://127.0.0.1:5000/ui",
        "endpoints": [
            "/api/status",
            "/api/satellites/live",
            "/api/satellites/tracked",
            "/api/satellites/history/<name>",
            "/api/satellites/passes/<name>",
            "/api/weather/current",
            "/api/weather/history/<metric>",
            "/api/analyze/decay",
            "/api/analyze/anomalies/<name>",
            "/api/analyze/correlate/<name>",
        ]
    })


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=5000)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--debug", action="store_true")
    args = parser.parse_args()

    print(f"\n  Deep Space Drifter API v0.3.0")
    print(f"  Running at http://{args.host}:{args.port}")
    print(f"  Docs: http://{args.host}:{args.port}/\n")
    app.run(host=args.host, port=args.port, debug=args.debug)
