#!/usr/bin/env python3
"""
deep-space-drifter / drifter.py
CLI entry point for v0.1.

Usage:
  python drifter.py                        # show all stations
  python drifter.py --group starlink       # show Starlink constellation
  python drifter.py --group visual         # brightest visible satellites
  python drifter.py --passes --lat 27.72 --lon 85.32   # passes over Kathmandu
  python drifter.py --watch                # live-refresh every 10s
  python drifter.py --find ISS             # find a specific satellite
"""

import sys
import time
import argparse
from datetime import datetime, timezone

sys.path.insert(0, __import__("pathlib").Path(__file__).parent.__str__())

from core.fetch import get_satellites
from core.propagate import build_satellite, get_position, get_positions_bulk, get_pass_window

GROUPS = ["stations_tle", "active", "starlink", "visual", "debris", "last-30-days"]

COL_W = {"name": 30, "lat": 8, "lon": 9, "alt": 10, "spd": 13}
HEADER = (
    f"{'Name':<{COL_W['name']}} "
    f"{'Lat':>{COL_W['lat']}} "
    f"{'Lon':>{COL_W['lon']}} "
    f"{'Alt (km)':>{COL_W['alt']}} "
    f"{'Speed (km/s)':>{COL_W['spd']}}"
)
DIVIDER = "-" * (sum(COL_W.values()) + len(COL_W))


def fmt_row(p: dict) -> str:
    if "error" in p:
        return f"{p['name']:<{COL_W['name']}}  !! {p['error'][:50]}"
    return (
        f"{p['name']:<{COL_W['name']}} "
        f"{p['lat']:>{COL_W['lat']}.2f} "
        f"{p['lon']:>{COL_W['lon']}.2f} "
        f"{p['alt_km']:>{COL_W['alt']}.1f} "
        f"{p['speed_kms']:>{COL_W['spd']}.3f}"
    )


def print_positions(positions: list[dict], group: str, epoch: str):
    print(f"\n  Deep Space Drifter  |  {group}  |  {epoch}")
    print(f"\n{HEADER}")
    print(DIVIDER)
    for p in positions:
        print(fmt_row(p))
    print(DIVIDER)
    print(f"  {len(positions)} satellites  |  press Ctrl+C to exit\n")


def cmd_positions(args):
    sats_raw = get_satellites(args.group, force_refresh=args.refresh)

    if args.find:
        query = args.find.upper()
        sats_raw = [s for s in sats_raw if query in s["name"].upper()]
        if not sats_raw:
            print(f"  No satellites matching '{args.find}'")
            return

    if args.watch:
        try:
            while True:
                positions = get_positions_bulk(sats_raw)
                epoch = positions[0]["epoch"] if positions else "n/a"
                print("\033[2J\033[H", end="")  # clear terminal
                print_positions(positions, args.group, epoch)
                time.sleep(args.interval)
        except KeyboardInterrupt:
            print("\n  Stopped.")
    else:
        positions = get_positions_bulk(sats_raw)
        epoch = positions[0]["epoch"] if positions else "n/a"
        print_positions(positions, args.group, epoch)


def cmd_passes(args):
    sats_raw = get_satellites(args.group, force_refresh=args.refresh)

    query = args.find or "ISS"
    matches = [s for s in sats_raw if query.upper() in s["name"].upper()]
    if not matches:
        print(f"  No satellites matching '{query}'")
        return

    target = matches[0]
    sat = build_satellite(target)
    passes = get_pass_window(
        sat,
        observer_lat=args.lat,
        observer_lon=args.lon,
        hours=args.hours,
    )

    print(f"\n  Passes for {target['name']}")
    print(f"  Observer: {args.lat}°N, {args.lon}°E  |  next {args.hours}h\n")

    if not passes:
        print(f"  No passes above 10° in the next {args.hours} hours.\n")
        return

    for i, p in enumerate(passes, 1):
        print(f"  Pass {i}")
        print(f"    Rise:  {p.get('rise_time', '?')}")
        print(f"    Peak:  {p.get('max_elevation_deg', '?')}° at {p.get('culmination_time', '?')}")
        print(f"    Set:   {p.get('set_time', '?')}")
        print()


def main():
    parser = argparse.ArgumentParser(
        prog="drifter",
        description="Deep Space Drifter — live satellite intelligence",
    )
    parser.add_argument("--group",    default="stations_tle", choices=GROUPS,
                        help="TLE catalog group to load")
    parser.add_argument("--find",     default=None,
                        help="Filter satellites by name (case-insensitive)")
    parser.add_argument("--passes",   action="store_true",
                        help="Show upcoming passes over observer location")
    parser.add_argument("--lat",      type=float, default=27.7172,
                        help="Observer latitude (default: Kathmandu)")
    parser.add_argument("--lon",      type=float, default=85.3240,
                        help="Observer longitude (default: Kathmandu)")
    parser.add_argument("--hours",    type=int,   default=24,
                        help="Look-ahead window for pass predictions (hours)")
    parser.add_argument("--watch",    action="store_true",
                        help="Live-refresh positions every N seconds")
    parser.add_argument("--interval", type=int,   default=10,
                        help="Refresh interval in seconds (used with --watch)")
    parser.add_argument("--refresh",  action="store_true",
                        help="Force fresh TLE fetch (ignore today's cache)")

    args = parser.parse_args()

    if args.passes:
        cmd_passes(args)
    else:
        cmd_positions(args)


if __name__ == "__main__":
    main()