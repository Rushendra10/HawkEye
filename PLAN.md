# HawkEye — the plan

Two people. 24 hours. Two demos. Nothing fancy that does not show up on stage.

## 0. Principles

1. **Hard part first.** The thing most likely to kill the project is the two-phone calibration
   (getting both cameras into one coordinate frame accurately). It is tested in the first 3 hours,
   on-phone, before any other code exists. If it fails the gate, we switch (see §5).
2. **Rushendra owns everything that can fail in a non-obvious way** (iOS, ARKit, camera, detection).
   Teammate owns everything that is deterministic math + plumbing (server, solver, dashboard) and
   can be developed and tested against synthetic data from minute zero.
3. **One place for data: the Mac.** Phones push JSON over HTTP to the Mac. The Mac serves the
   dashboard. No peer-to-peer, no Bluetooth, no WebSockets, no app on the judge's phone.
4. **Phones never move after calibration.** This removes 80% of the complexity (no per-frame pose,
   no drift handling, no format switching).
5. **60 fps inside ARKit for v1.** ARKit hands us the camera image, the pose and the intrinsics
   together every frame. 240 fps is a stretch goal, not a requirement for an underhand arc or a wall
   bounce.
6. **No feature after T+19h.** From then on: rehearsals, slides, backup video.

## 1. The two demos (what "done" means)

**Demo A — arc throw.** Phones ~3 m apart, both seeing a ~4 m wide volume. Underhand lob, peak
~2 m. Dashboard shows: the 3D arc, release speed, launch angle, apex height, flight time, and the
fitted gravity `g` (target 9.8 ± 0.3 m/s²) with the direction error vs. ARKit's gravity (< 5°).

**Demo B — wall bounce.** Same setup, with a wall at the far side of the volume. Throw at the wall,
catch the return. Dashboard shows: two arcs split at the impact, speed in / speed out, impact point,
restitution (speed retained along the bounce normal), and `g` fitted independently on both legs.

**Proof-of-reality beat (both demos):** drop the ball from rest → `g = 9.8` on screen.

## 2. Roles

### Rushendra — iOS app (`ios/`, spec in `docs/IOS.md`)
- Xcode install, free-account signing on both phones.
- ARKit session @ 60 fps with image-anchor calibration against the marker.
- On-phone ball detection by chroma threshold on the camera frame.
- Clock sync with the server; POST calibration and detection batches.
- Owns the go/no-go test at T+3h (baseline check, §4).
- Later: 240 fps stretch, AR trail overlay (only if everything else is done).

### Teammate — server, solver, dashboard (`server/`, spec in `docs/API.md` + `docs/MATH.md`)
- FastAPI server with 4 endpoints, logging every request to JSONL on disk.
- Simulator that generates synthetic two-camera detections conforming to the API (so the solver
  is developed and tested before any phone data exists).
- Solver: rays → triangulation → time-offset refinement → bounce segmentation → parabola fits →
  metrics → validation numbers.
- Dashboard: one HTML page, Plotly, auto-refresh.
- Later: "error vs. number of phones / angle" chart from the simulator, for the slides.

The teammate's work is fully specified by `docs/API.md` and `docs/MATH.md`. An agent can pick it
up from those two files alone. Development machine: teammate's own laptop (any OS). The server
runs on the Mac at demo time (clone, `pip install -r requirements.txt`, run).

## 3. Timeline (T+0 = the moment we start building)

| Time | Rushendra (iOS) | Teammate (server/solver) | Gate / decision |
|---|---|---|---|
| T+0 → T+1 | Xcode downloading. Meanwhile: Developer Mode on both phones; read `docs/IOS.md`; set up hotspot; measure marker width | Repo clone, venv, FastAPI skeleton with the 4 endpoints + JSONL logging (`docs/API.md`) | Hotspot up; Mac IP known |
| T+1 → T+3 | **Calibration**: ARKit 60 fps + image anchor. Phone shows its own position in the marker frame on screen. Both phones placed, both lock. | Simulator (`simulate.py`) posting synthetic calibration + detections; solver v0 triangulates and recovers `g` on synthetic data | **GATE 1 (T+3h): baseline check.** Distance between the two phones computed from the two calibrations vs. a tape measure. Pass: within 5 cm. Fail → §5 |
| T+3 → T+5 | **Detection**: chroma threshold on the CbCr plane, centroid + pixel count; "Sample ball" button; on-screen `n, u, v` readout | Dashboard v0 (2D tracks per camera, then 3D). Solver reads real JSONL once it exists | Detection ≥ 50 fps with a bright ball at 4 m |
| T+5 → T+6 | Clock sync + POST batches wired | Solver on the first real capture | **GATE 2 (T+6h): first real 3D arc; drop test `g` within 9.8 ± 1.0**. Fail → debug sign conventions (`docs/MATH.md` §8) before anything else |
| T+6 → T+10 | Robustness: tolerance slider, reject blobs that are too big/small, re-sync, settings persistence | Δt refinement, bounce segmentation, metrics, restitution, dashboard polish | Wall bounce works end to end |
| T+10 → T+12 | Rehearse in the real demo spot, both demos, 10 drops | Log every run; compute `g` mean/std | **GATE 3 (T+12h): repeatable.** `g` std < 0.3 over 10 drops. Feature list frozen here |
| T+12 → T+16 | Sleep in shifts (3–4 h each). Not optional. | | |
| T+16 → T+19 | Stretch only if GATE 3 passed cleanly: 240 fps capture, or AR trail on phone | N-phones error chart; slides; README; repo tidy | Backup video of one clean run of each demo recorded |
| T+19 → T+21 | 5 full rehearsals, code freeze | Same | |
| T+21 → T+22 | Submit (slides + repo) before Sunday 12:00 | | Done |

If the hackathon clock does not leave 22 h, compress T+6→T+10 and T+16→T+19; never compress
T+0→T+6 or the rehearsals.

## 4. Gates in detail

**GATE 1 — baseline check (calibration is real).** Each phone, once it locks on the marker, shows
its camera position in the marker frame `(x, y, z)` on screen. Compute the distance between the two
phones' positions by hand (or the server's `/latest` shows it once calibrations are posted).
Measure the real distance between the two phones' cameras with a tape measure.
- Within 5 cm at ~3 m baseline: pass.
- 5–15 cm: pass with a note; later refine extrinsics using the ball tracks (stretch).
- > 15 cm or lock unreliable: fail → §5.

**GATE 2 — first physics.** Drop the ball from rest between the phones. The solver fits
`p(t) = p0 + v0 t + ½ a t²`. Pass if `|a|` is within 9.8 ± 1.0 and `a` points within 10° of ARKit's
"down". A wrong sign anywhere (image v axis, camera forward axis) shows up here as `g` pointing
sideways or up; the fix table is in `docs/MATH.md` §8.

**GATE 3 — repeatable.** 10 drops: mean `g` within ±0.3 of 9.8, std < 0.3. This number goes on a
slide. From here on, no new features except the stretch list.

## 5. Kill-switches

- **Calibration via ARKit image anchor fails GATE 1** → fallback A: OpenCV checkerboard stereo
  calibration done by the teammate (both phones photograph a printed checkerboard from their fixed
  positions; `cv2.stereoCalibrate` gives extrinsics; intrinsics still from ARKit). Costs ~1 h and the
  "no target" line in the pitch. Nothing else changes.
- **ARKit itself is unusable (tracking lost constantly in the venue lighting)** → fallback B: same
  OpenCV stereo calibration plus plain AVFoundation capture at 60/240 fps. Loses ARKit entirely; math
  unchanged.
- **Detection cannot keep up or the ball cannot be separated from the background by T+5h** →
  switch detector to Vision's `VNDetectTrajectoriesRequest` (built for thrown objects from a static
  camera). If that also fails, record clips and detect offline on the Mac with OpenCV (slower demo
  loop, still a demo).
- **Nothing works by T+6h** → stop, regroup, and run Soundscope (acoustic camera, see chat
  history) which shares the ARKit skeleton. This decision is made at T+6h, not later.

## 6. Hardware / logistics

- Phones: iPhone 16 (Rushendra), iPhone 16 Pro Max (teammate). Both fine; LiDAR not used.
- Laptop: one Mac (Rushendra) — Xcode + server at demo. Teammate's laptop — server/solver dev.
- Network: one phone's **Personal Hotspot**; everything joins it. Mac IP is the server address.
- Ball: bright, matte, single color (tennis ball or orange foam ball). Nothing shiny. Have two.
- Phone stands: two water bottles or two laptops' edges. Phones landscape, resting, not held.
- Power: both phones plugged in during rehearsals (ARKit at 60 fps drains battery).
- Marker: `marker/marker.html` fullscreen on the Mac, width measured with a ruler.

## 7. Decisions log (so nobody relitigates)

- 60 fps inside ARKit, not 240 fps AVFoundation, for v1. Reason: pose + intrinsics + image arrive
  together; zero format-switching risk. 240 fps is a stretch.
- Image-anchor calibration, not ARKit collaborative sessions. Reason: deterministic, one-shot,
  no Multipeer, no relocalization dance; both phones only need to see the same image once.
- HTTP POST batches, not WebSockets. Reason: nothing here needs sub-second latency; a throw is
  solved after it lands.
- Phones stream detections continuously; the server detects throw events. Reason: no Record button,
  no coordination between phones.
- Clock sync = HTTP ping (min-RTT) on the phone + Δt refinement in the solver by minimizing
  triangulation residual. Reason: no audio, no clap, nothing to go wrong on stage.
- Public GitHub repo. Reason: judges need to open it.
