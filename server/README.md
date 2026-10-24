# server — teammate's half

Read, in order: `../docs/API.md` (the contract), `../docs/MATH.md` (the solver), `../PLAN.md` §3
(what is due when). Everything you need is in those three files.

## Build order

1. `app.py` — FastAPI with `GET /time`, `POST /calibration`, `POST /detections`, `GET /latest`,
   `POST /reset`, static dashboard. Every POST body appended to `data/<session>/*.jsonl`
   with `received_at`. Run with `uvicorn app:app --host 0.0.0.0 --port 8000`.
2. `simulate.py` — synthetic two-camera throws conforming to the API (MATH.md §9). Can POST to a
   running server or write JSONL. **This exists before any real data does.**
3. `solver.py` — MATH.md §1–§7, runnable as `python solver.py data/<session>/` and importable by
   `app.py`. Test against the simulator until `g` comes back within ±0.2.
4. `static/index.html` — the dashboard (MATH.md §10). Plotly from CDN, polls `/latest`.
5. Real data: Rushendra will commit the first real session under `data/` (small files). Run the
   solver on it; expect to hit a sign issue once — MATH.md §8.
6. Δt refinement, bounce segmentation, restitution, drop statistics.
7. Slides chart: error vs number of cameras / angle, from the simulator.

## Constraints

- Python 3.9 compatible (the Mac that runs this at demo time has 3.9): no `match`, use
  `typing.Optional[...]`, `list[...]` is fine only with `from __future__ import annotations`.
- Dependencies: fastapi, uvicorn, numpy, scipy. Nothing else unless it saves an hour.
- No database, no auth, no websockets. In-memory state + JSONL logs.
- Keep `solver.py` free of FastAPI imports so it runs offline.

## Running at the demo

On the Mac: `git pull`, `source .venv/bin/activate`, `uvicorn app:app --host 0.0.0.0 --port 8000`.
Dashboard on the projector at `http://<mac-ip>:8000/`.
