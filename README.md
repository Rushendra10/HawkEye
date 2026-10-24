# HawkEye — two iPhones, one 3D ball tracker

Put two ordinary iPhones down a few meters apart, pointed at the same space from two angles.
Throw a ball. A laptop shows the ball's real 3D flight: speed, launch angle, apex, bounce point,
and — as proof it is real — the measured gravitational acceleration (should read 9.8 m/s²).

No court lines, no tripods, no calibration target beyond glancing at the laptop screen once,
no hardware. Built in 24 hours at Social Hack (UMN), theme **Connect & Intersect**: two views
connected, rays intersecting.

## How it works (one paragraph)

Each phone runs ARKit. Both phones look at the same marker image shown on the laptop, which puts
both cameras in one shared coordinate frame (ARKit gives each camera's pose relative to the marker
and its lens intrinsics for free). From then on the phones stay still. Each phone detects the ball
in every camera frame by color (a bright matte ball) and streams `(time, u, v)` pixel detections
to a small Python server on the Mac. The server turns each detection into a 3D ray, intersects the
two rays frame by frame, splits the track at bounces, fits a parabola to each flight segment, and
reports the physics. A browser dashboard draws it.

## Repo layout

```
PLAN.md            roles, fail-fast order, timeline, gates, kill-switches   <- read this first
docs/API.md        the contract between the iOS app and the server (JSON, units, conventions)
docs/MATH.md       the solver, step by step, with validation tests
docs/IOS.md        the iOS app spec (Rushendra)
docs/DEMO.md       setup checklist, the two demos, judge Q&A
ios/               Xcode project (Rushendra)
server/            Python server + solver + dashboard (teammate)
marker/            the calibration marker image + a page that shows it at a known width
```

## Quickstart

**Server (any OS, Python 3.9+):**

```bash
cd server
python3 -m venv .venv && source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn app:app --host 0.0.0.0 --port 8000
# dashboard: http://<this-machine-ip>:8000/
```

**Marker:** open `marker/marker.html` in a browser on the Mac, fullscreen it, measure the drawn
width of the image with a ruler (≈ 0.30 m on a 14" MacBook), enter that number in the app.

**Phones:** build `ios/` from Xcode onto both phones (free Apple ID is enough), set server URL,
device name, marker width. Place phones, lock calibration on both, throw.

## Network (important)

eduroam blocks device-to-device traffic. Everything (both phones, the Mac, the teammate's laptop)
joins **one phone's Personal Hotspot**. The server runs on the Mac. Phones talk to the Mac's
hotspot IP over plain HTTP.
