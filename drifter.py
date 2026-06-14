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
from core import storage
from core import spaceweather

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
                if args.log:
                    n = storage.save_positions(positions)
                    print(f"  [log] saved {n} positions")
                print("\033[2J\033[H", end="")  # clear terminal
                print_positions(positions, args.group, epoch)
                time.sleep(args.interval)
        except KeyboardInterrupt:
            print("\n  Stopped.")
    else:
        positions = get_positions_bulk(sats_raw)
        epoch = positions[0]["epoch"] if positions else "n/a"
        if args.log:
            n = storage.save_positions(positions)
            print(f"  [log] saved {n} positions to {storage.DB_PATH.name}")
        print_positions(positions, args.group, epoch)


def cmd_weather(args):
    print("Fetching space weather from NOAA SWPC...")
    conditions = spaceweather.get_current_conditions()

    print(f"\n  Deep Space Drifter  |  Space Weather")
    print(f"{'='*50}")
    print(f"  Kp index:        {conditions['kp_current']}  ({conditions['kp_status']})")
    print(f"  Storm level:     {conditions['storm_level']}")
    print(f"  Time:            {conditions['kp_time']}")
    print()
    print(f"  Solar wind speed:   {conditions['solar_wind_speed_kms']} km/s")
    print(f"  Solar wind density: {conditions['solar_wind_density_pcm3']} p/cm³")
    print(f"  Measured at:        {conditions['solar_wind_time']}")
    print()
    if conditions["kp_max_predicted"]:
        print(f"  Forecast peak Kp:   {conditions['kp_max_predicted']} at {conditions['kp_max_time']}")
    print(f"{'='*50}\n")

    if args.log:
        kp_points = spaceweather.fetch_kp_index()
        plasma_points = spaceweather.fetch_solar_wind("plasma_1day")
        n = storage.save_weather_points(kp_points + plasma_points)
        print(f"  [log] saved {n} new weather points to {storage.DB_PATH.name}")


def cmd_history(args):
    if args.metric:
        # space weather history
        rows = storage.get_weather_history(args.metric, limit=args.limit)
        if not rows:
            print(f"  No history for metric '{args.metric}'. Run 'weather --log' first.")
            return
        print(f"\n  Space weather history: {args.metric} (most recent {len(rows)})\n")
        print(f"  {'Time':<24} {'Value':>10}  {'Status':<10} {'Source'}")
        print(f"  {'-'*60}")
        for r in rows:
            status = r.get("status") or ""
            print(f"  {r['time_tag']:<24} {r['value']:>10.2f}  {status:<10} {r['source']}")
        return

    if not args.name:
        tracked = storage.get_tracked_satellites()
        if not tracked:
            print("  No satellite history recorded yet. Run with --log to start logging.")
            return
        print(f"\n  Tracked satellites ({len(tracked)}):\n")
        for name in tracked:
            print(f"    {name}")
        print(f"\n  Use 'history --name \"<satellite>\"' to view position history.")
        return

    rows = storage.get_position_history(args.name, limit=args.limit)
    if not rows:
        print(f"  No history for '{args.name}'. Run with --log first, or check the name with 'history' (no args).")
        return

    print(f"\n  Position history: {args.name} (most recent {len(rows)})\n")
    print(f"  {'Epoch':<24} {'Lat':>8} {'Lon':>9} {'Alt (km)':>10} {'Speed':>8}")
    print(f"  {'-'*65}")
    for r in rows:
        print(f"  {r['epoch']:<24} {r['lat']:>8.2f} {r['lon']:>9.2f} {r['alt_km']:>10.1f} {r['speed_kms']:>8.3f}")


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
    subparsers = parser.add_subparsers(dest="command")

    # --- positions (default) ---
    pos_parser = subparsers.add_parser("positions", help="Track satellite positions (default)")
    _add_position_args(pos_parser)

    # --- weather ---
    weather_parser = subparsers.add_parser("weather", help="Show current space weather")
    weather_parser.add_argument("--log", action="store_true",
                                 help="Save fetched weather data to local database")

    # --- history ---
    history_parser = subparsers.add_parser("history", help="View logged history")
    history_parser.add_argument("--name", default=None,
                                 help="Satellite name to view position history for")
    history_parser.add_argument("--metric", default=None,
                                 help="Space weather metric to view (e.g. kp, speed, density)")
    history_parser.add_argument("--limit", type=int, default=20,
                                 help="Number of records to show (default: 20)")

    # Also support running with no subcommand (legacy / default behavior = positions)
    _add_position_args(parser)

    args = parser.parse_args()

    if args.command == "weather":
        cmd_weather(args)
    elif args.command == "history":
        cmd_history(args)
    elif args.command == "positions" or args.command is None:
        if getattr(args, "passes", False):
            cmd_passes(args)
        else:
            cmd_positions(args)


def _add_position_args(p: argparse.ArgumentParser):
    """Shared args for position tracking, used by both the subcommand and legacy top-level parser."""
    p.add_argument("--group",    default="stations_tle", choices=GROUPS,
                    help="TLE catalog group to load")
    p.add_argument("--find",     default=None,
                    help="Filter satellites by name (case-insensitive)")
    p.add_argument("--passes",   action="store_true",
                    help="Show upcoming passes over observer location")
    p.add_argument("--lat",      type=float, default=27.7172,
                    help="Observer latitude (default: Kathmandu)")
    p.add_argument("--lon",      type=float, default=85.3240,
                    help="Observer longitude (default: Kathmandu)")
    p.add_argument("--hours",    type=int,   default=24,
                    help="Look-ahead window for pass predictions (hours)")
    p.add_argument("--watch",    action="store_true",
                    help="Live-refresh positions every N seconds")
    p.add_argument("--interval", type=int,   default=10,
                    help="Refresh interval in seconds (used with --watch)")
    p.add_argument("--refresh",  action="store_true",
                    help="Force fresh TLE fetch (ignore today's cache)")
    p.add_argument("--log",      action="store_true",
                    help="Save fetched positions to local database")


if __name__ == "__main__":
    main()