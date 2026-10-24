# HawkEye — two iPhones, one 3D ball tracker

Put two ordinary phones down a few meters apart, pointed at the same space from two angles.
Throw a ball. A laptop shows the ball's real 3D flight: speed, launch angle, apex, bounce point,
and — as proof it is real — the measured gravitational acceleration (should read 9.8 m/s²).

No court lines, no tripods, no app install: the phones run a web page. They look at the laptop
screen once (a checkerboard) and that puts both cameras in one coordinate frame.
Built in 24 hours at Social Hack (UMN), theme **Connect & Intersect**: two views connected, rays
intersecting.

## How it works (one paragraph)

Each phone opens `capture.html` in Safari. A chessboard shown on the laptop gives each phone's
lens parameters (8 photos) and its position and orientation (1 photo, `solvePnP`). From then on
the phones stay still. Each phone detects the ball in every camera frame by color and streams
`(time, u, v)` pixel detections to a small Python server on the Mac. The server turns each
detection into a 3D ray, intersects the two rays frame by frame, splits the track at bounces,
fits a parabola to each flight segment, and reports the physics. A browser dashboard draws it.

## Repo layout

```
PLAN.md             roles, fail-fast order, timeline, gates, kill-switches   <- read this first
docs/API.md         the contract between the capture page and the server
docs/MATH.md        calibration + solver, step by step, with validation tests
docs/WEB.md         the capture page spec (Rushendra)
docs/DEMO.md        setup checklist, the two demos, judge Q&A
server/             FastAPI server + OpenCV calibration + solver + dashboard (teammate)
server/static/      capture.html (Rushendra), board.html + index.html (teammate)
marker/             (unused now; kept from the ARKit plan)
```

## Quickstart

```bash
cd server
python3 -m venv .venv && source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn app:app --host 0.0.0.0 --port 8443 --ssl-certfile certs/cert.pem --ssl-keyfile certs/key.pem
# phones:    https://<mac-ip>:8443/static/capture.html
# dashboard: https://<mac-ip>:8443/
```

HTTPS is required (Safari only exposes the camera on secure origins). `docs/WEB.md` §0 has the
two-minute `mkcert` setup.

## Network

eduroam blocks device-to-device traffic. Everything joins one phone's **Personal Hotspot**.
The server runs on the Mac.
