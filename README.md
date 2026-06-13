<p align="center">
  <img src="assets/logo.png" alt="Deep Space Drifter" width="280"/>
</p>

# Deep Space Drifter

> Observe. Analyze. Discover.

An open-source space intelligence platform for tracking satellites, debris,
and spacecraft using publicly available orbital data — built to grow into a
living observatory of humanity's presence beyond Earth.

## What it does (v0.1)

- Fetches live TLE (orbital element) data from CelesTrak
- Propagates real-time satellite positions using SGP4 (via Skyfield)
- Computes pass predictions for any ground location
- CLI with live-refresh tracking, name filtering, and multiple satellite groups
- Daily local caching to avoid redundant API calls

## Quick start

```bash
git clone https://github.com/flawnlawyer/deep-space-drifter.git
cd deep-space-drifter
pip install -r requirements.txt

python drifter.py
```

## Usage

```bash
python drifter.py                          # space stations (default)
python drifter.py --group starlink         # Starlink constellation
python drifter.py --group visual           # brightest visible satellites
python drifter.py --find ISS               # filter by name

python drifter.py --passes --hours 48      # ISS passes over observer
python drifter.py --passes --lat 27.7172 --lon 85.3240  # custom location

python drifter.py --watch --interval 5     # live refresh every 5s
python drifter.py --refresh                # force fresh TLE fetch
```

Default observer location is Kathmandu, Nepal. Pass `--lat` / `--lon` to override.

## Architecture

```
core/
  fetch.py       — TLE retrieval + caching from CelesTrak
  propagate.py   — SGP4 orbital propagation, pass prediction
drifter.py        — CLI entry point
tests/
  test_pipeline.py — unit tests with real TLE fixtures (no network required)
```

## Roadmap

- [x] v0.1 — TLE fetch, SGP4 propagation, CLI tracker
- [ ] v0.2 — Space weather correlation (NOAA Kp index, solar wind)
- [ ] v0.2 — SQLite time-series storage for historical replay
- [ ] v0.3 — Anomaly detection on maneuver patterns
- [ ] v0.3 — Web frontend with CesiumJS 3D globe
- [ ] v0.4 — Conjunction (collision) risk scoring
- [ ] v0.4 — Alerting (email / webhook / Discord)

## Data sources

- [CelesTrak](https://celestrak.org) — TLE / orbital element sets
- NOAA SWPC (planned) — space weather data
- NASA APIs (planned) — mission and event data

## Tech stack

Python · Skyfield (SGP4) · requests

## Contributing

This is an early-stage open-source project. Issues, feature ideas, and PRs
are welcome — especially around data source integrations, propagation
accuracy, and visualization.

## License

MIT
