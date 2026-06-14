<p align="center">
  <img src="assets/logo.png" alt="Deep Space Drifter" width="280"/>
</p>

# Deep Space Drifter

> Observe. Analyze. Discover.

An open-source space intelligence platform for tracking satellites, debris,
and spacecraft using publicly available orbital data — built to grow into a
living observatory of humanity's presence beyond Earth.

## What it does

**v0.1**
- Fetches live TLE (orbital element) data from CelesTrak
- Propagates real-time satellite positions using SGP4 (via Skyfield)
- Computes pass predictions for any ground location
- CLI with live-refresh tracking, name filtering, and multiple satellite groups
- Daily local caching to avoid redundant API calls

**v0.2**
- SQLite time-series storage for satellite positions and space weather
- Space weather monitoring via NOAA SWPC (Kp index, solar wind speed/density)
- `--log` flag to persist position snapshots and weather readings
- `history` command to review logged data
- Geomagnetic storm classification (G1–G5 scale)

## Quick start

```bash
git clone https://github.com/flawnlawyer/deep-space-drifter.git
cd deep-space-drifter
pip install -r requirements.txt

python drifter.py
```

## Usage

```bash
# Position tracking
python drifter.py                          # space stations (default)
python drifter.py --group starlink         # Starlink constellation
python drifter.py --group visual           # brightest visible satellites
python drifter.py --find ISS               # filter by name

python drifter.py --passes --hours 48      # ISS passes over observer
python drifter.py --passes --lat 27.7172 --lon 85.3240  # custom location

python drifter.py --watch --interval 5     # live refresh every 5s
python drifter.py --watch --log            # live refresh + log to SQLite
python drifter.py --refresh                # force fresh TLE fetch

# Space weather
python drifter.py weather                  # current Kp, solar wind
python drifter.py weather --log            # fetch + save to SQLite

# History
python drifter.py history                  # list tracked satellites
python drifter.py history --name "ISS (ZARYA)"   # position history
python drifter.py history --metric kp            # space weather history
python drifter.py history --metric speed --limit 50
```

Default observer location is Kathmandu, Nepal. Pass `--lat` / `--lon` to override.
All data is stored locally in `data/drifter.db` (SQLite).

## Architecture

```
core/
  fetch.py         — TLE retrieval + caching from CelesTrak
  propagate.py     — SGP4 orbital propagation, pass prediction
  storage.py       — SQLite time-series storage (positions, space weather)
  spaceweather.py  — NOAA SWPC fetcher (Kp index, solar wind)
drifter.py          — CLI entry point
tests/
  test_pipeline.py         — TLE/propagation tests (real fixtures, no network)
  test_storage_weather.py  — storage + space weather parsing tests
```

## Roadmap

- [x] v0.1 — TLE fetch, SGP4 propagation, CLI tracker
- [x] v0.2 — Space weather monitoring (NOAA Kp index, solar wind)
- [x] v0.2 — SQLite time-series storage for historical replay
- [ ] v0.3 — Anomaly detection on maneuver patterns
- [ ] v0.3 — Web frontend with CesiumJS 3D globe
- [ ] v0.4 — Conjunction (collision) risk scoring
- [ ] v0.4 — Alerting (email / webhook / Discord)

## Data sources

- [CelesTrak](https://celestrak.org) — TLE / orbital element sets
- [NOAA SWPC](https://www.swpc.noaa.gov) — space weather (Kp index, solar wind)
- NASA APIs (planned) — mission and event data

## Tech stack

Python · Skyfield (SGP4) · requests

## Contributing

This is an early-stage open-source project. Issues, feature ideas, and PRs
are welcome — especially around data source integrations, propagation
accuracy, and visualization.

## License

MIT
