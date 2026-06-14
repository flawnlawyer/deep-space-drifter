"""
deep-space-drifter / core / storage.py
SQLite-backed time-series storage for satellite positions and space weather.
"""

import sqlite3
from pathlib import Path
from contextlib import contextmanager
from datetime import datetime, timezone

DB_PATH = Path(__file__).parent.parent / "data" / "drifter.db"
DB_PATH.parent.mkdir(parents=True, exist_ok=True)


SCHEMA = """
CREATE TABLE IF NOT EXISTS positions (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    name        TEXT    NOT NULL,
    lat         REAL    NOT NULL,
    lon         REAL    NOT NULL,
    alt_km      REAL    NOT NULL,
    speed_kms   REAL    NOT NULL,
    epoch       TEXT    NOT NULL,
    recorded_at TEXT    NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_positions_name_epoch
    ON positions (name, epoch);

CREATE TABLE IF NOT EXISTS space_weather (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    metric      TEXT    NOT NULL,    -- 'kp', 'solar_wind_speed', 'solar_wind_density', 'bz'
    value       REAL    NOT NULL,
    time_tag    TEXT    NOT NULL,    -- timestamp from source data
    source      TEXT    NOT NULL,    -- 'noaa_kp_forecast', 'noaa_plasma', 'noaa_mag'
    status      TEXT,               -- 'observed', 'estimated', 'predicted' (kp only)
    recorded_at TEXT    NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_weather_metric_time
    ON space_weather (metric, time_tag);

CREATE UNIQUE INDEX IF NOT EXISTS idx_weather_unique
    ON space_weather (metric, time_tag, source);
"""


@contextmanager
def get_db():
    """Context-managed SQLite connection with row factory."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db():
    """Create tables if they don't exist. Safe to call repeatedly."""
    with get_db() as conn:
        conn.executescript(SCHEMA)


# ── Position storage ─────────────────────────────────────────────────────────

def save_positions(positions: list[dict]):
    """
    Save a batch of position snapshots.
    Expects dicts with: name, lat, lon, alt_km, speed_kms, epoch.
    Skips entries with 'error' key.
    """
    init_db()
    rows = [
        (p["name"], p["lat"], p["lon"], p["alt_km"], p["speed_kms"], p["epoch"])
        for p in positions
        if "error" not in p
    ]
    if not rows:
        return 0

    with get_db() as conn:
        conn.executemany(
            "INSERT INTO positions (name, lat, lon, alt_km, speed_kms, epoch) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            rows,
        )
    return len(rows)


def get_position_history(name: str, limit: int = 100) -> list[dict]:
    """Return most recent position snapshots for a satellite, newest first."""
    init_db()
    with get_db() as conn:
        cur = conn.execute(
            "SELECT name, lat, lon, alt_km, speed_kms, epoch, recorded_at "
            "FROM positions WHERE name = ? "
            "ORDER BY epoch DESC LIMIT ?",
            (name, limit),
        )
        return [dict(row) for row in cur.fetchall()]


def get_tracked_satellites() -> list[str]:
    """Return distinct satellite names that have stored history."""
    init_db()
    with get_db() as conn:
        cur = conn.execute("SELECT DISTINCT name FROM positions ORDER BY name")
        return [row["name"] for row in cur.fetchall()]


def count_positions() -> int:
    init_db()
    with get_db() as conn:
        cur = conn.execute("SELECT COUNT(*) AS n FROM positions")
        return cur.fetchone()["n"]


# ── Space weather storage ────────────────────────────────────────────────────

def save_weather_points(points: list[dict]):
    """
    Save space weather data points.
    Expects dicts with: metric, value, time_tag, source, status (optional).
    Uses INSERT OR IGNORE to dedupe on (metric, time_tag, source).
    """
    init_db()
    rows = [
        (p["metric"], p["value"], p["time_tag"], p["source"], p.get("status"))
        for p in points
    ]
    if not rows:
        return 0

    with get_db() as conn:
        cur = conn.executemany(
            "INSERT OR IGNORE INTO space_weather (metric, value, time_tag, source, status) "
            "VALUES (?, ?, ?, ?, ?)",
            rows,
        )
        return cur.rowcount


def get_latest_weather(metric: str) -> dict | None:
    """Return the most recent data point for a given metric."""
    init_db()
    with get_db() as conn:
        cur = conn.execute(
            "SELECT * FROM space_weather WHERE metric = ? "
            "ORDER BY time_tag DESC LIMIT 1",
            (metric,),
        )
        row = cur.fetchone()
        return dict(row) if row else None


def get_weather_history(metric: str, limit: int = 100) -> list[dict]:
    """Return recent data points for a metric, newest first."""
    init_db()
    with get_db() as conn:
        cur = conn.execute(
            "SELECT * FROM space_weather WHERE metric = ? "
            "ORDER BY time_tag DESC LIMIT ?",
            (metric, limit),
        )
        return [dict(row) for row in cur.fetchall()]


def count_weather_points() -> int:
    init_db()
    with get_db() as conn:
        cur = conn.execute("SELECT COUNT(*) AS n FROM space_weather")
        return cur.fetchone()["n"]


if __name__ == "__main__":
    init_db()
    print(f"Database initialized at: {DB_PATH}")
    print(f"  positions:     {count_positions()} rows")
    print(f"  space_weather: {count_weather_points()} rows")
    print(f"  tracked sats:  {get_tracked_satellites()}")
