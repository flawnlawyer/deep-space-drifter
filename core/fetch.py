"""
deep-space-drifter / core / fetch.py
Fetch TLE data from CelesTrak and cache locally.
"""

import os
import json
import time
import requests
from datetime import datetime, timezone
from pathlib import Path

CATALOG_URLS = {
    "stations_tle": "https://celestrak.org/NORAD/elements/gp.php?GROUP=stations&FORMAT=tle",
    "active":       "https://celestrak.org/NORAD/elements/gp.php?GROUP=active&FORMAT=tle",
    "starlink":     "https://celestrak.org/NORAD/elements/gp.php?GROUP=starlink&FORMAT=tle",
    "debris":       "https://celestrak.org/NORAD/elements/gp.php?GROUP=cosmos-2251-debris&FORMAT=tle",
    "visual":       "https://celestrak.org/NORAD/elements/gp.php?GROUP=visual&FORMAT=tle",
    "last-30-days": "https://celestrak.org/NORAD/elements/gp.php?GROUP=last-30-days&FORMAT=tle",
}

RAW_DIR = Path(__file__).parent.parent / "data" / "raw"
RAW_DIR.mkdir(parents=True, exist_ok=True)


def fetch_tle_group(group: str = "stations_tle") -> list[dict]:
    """
    Fetch a TLE group from CelesTrak.
    Returns a list of dicts: {name, line1, line2}
    Caches to data/raw/<group>_<date>.tle
    """
    if group not in CATALOG_URLS:
        raise ValueError(f"Unknown group '{group}'. Choose from: {list(CATALOG_URLS)}")

    url = CATALOG_URLS[group]
    print(f"[fetch] Requesting {group} from CelesTrak...")

    headers = {"User-Agent": "Mozilla/5.0 (DeepSpaceDrifter/0.1; +https://github.com/flawnlawyer/deep-space-drifter)"}
    resp = requests.get(url, headers=headers, timeout=15)
    resp.raise_for_status()
    raw = resp.text.strip()

    if not raw or "1 " not in raw or "2 " not in raw:
        raise ValueError(
            f"Unexpected response from CelesTrak for group '{group}'. "
            f"Got {len(raw)} chars, doesn't look like TLE data. "
            f"First 200 chars: {raw[:200]!r}"
        )

    satellites = _parse_tle_text(raw)

    cache_path = RAW_DIR / f"{group}_{datetime.now(timezone.utc).strftime('%Y%m%d')}.tle"
    cache_path.write_text(raw)
    print(f"[fetch] Cached {len(satellites)} satellites → {cache_path.name}")

    return satellites


def _parse_tle_text(raw: str) -> list[dict]:
    """Parse raw TLE text (3-line format) into structured dicts."""
    lines = [l.strip() for l in raw.splitlines() if l.strip()]
    satellites = []

    i = 0
    while i < len(lines) - 2:
        name  = lines[i]
        line1 = lines[i + 1]
        line2 = lines[i + 2]

        if line1.startswith("1 ") and line2.startswith("2 "):
            satellites.append({
                "name":  name,
                "line1": line1,
                "line2": line2,
            })
            i += 3
        else:
            i += 1

    return satellites


def load_cached(group: str = "stations_tle") -> list[dict] | None:
    """
    Load today's cached TLE file if it exists.
    Returns None if no cache found — caller should fetch fresh.
    """
    today = datetime.now(timezone.utc).strftime("%Y%m%d")
    cache_path = RAW_DIR / f"{group}_{today}.tle"

    if cache_path.exists():
        print(f"[fetch] Using cache: {cache_path.name}")
        return _parse_tle_text(cache_path.read_text())

    return None


def get_satellites(group: str = "stations_tle", force_refresh: bool = False) -> list[dict]:
    """
    Main entry point. Returns parsed TLE list.
    Uses today's cache if available, fetches fresh otherwise.
    """
    if not force_refresh:
        cached = load_cached(group)
        if cached:
            return cached

    return fetch_tle_group(group)


if __name__ == "__main__":
    sats = get_satellites("stations_tle")
    print(f"\n{'='*50}")
    print(f"  Fetched {len(sats)} satellites")
    print(f"{'='*50}")
    for s in sats[:5]:
        print(f"  {s['name']}")
    if len(sats) > 5:
        print(f"  ... and {len(sats) - 5} more")