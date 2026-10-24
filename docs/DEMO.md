# Demo — setup checklist, scripts, judge Q&A

## Setup checklist (12 minutes, same order every time)

1. Hotspot on. Mac + both phones joined. Mac IP matches the cert (else `mkcert` again, 10 s).
2. Mac: `uvicorn app:app --host 0.0.0.0 --port 8443 --ssl-certfile certs/cert.pem --ssl-keyfile certs/key.pem`.
   Projector: `https://<mac>:8443/`. Reset.
3. Place the phones: landscape, resting on bottles, ~3 m apart, each angled ~30° toward the
   center of the throwing volume, lens height 0.6–1.2 m, plugged in. Both see the whole arc and
   the wall (Demo B). Do not touch them again.
4. Both phones: Safari → `https://<mac>:8443/static/capture.html`. Camera visible.
   (Intrinsics were done Saturday; skip unless the stream resolution changed — check the status line.)
5. Board: `board.html` fullscreen on the Mac, lid vertical, placed ~2 m from each phone, facing
   both. Tap **Lock** on both. Dashboard shows both cameras and the baseline. Sanity: baseline ≈ tape.
6. Remove the Mac. Both phones → **Live**. Dashboard: both cameras alive.
7. Hold the ball at the crosshair → **Sample ball** on both (lighting may have changed).
8. Drop test. `g` on screen. Not within 9.8 ± 0.5 → re-lock (step 5) before demoing.
9. Second ball in your pocket.

## Demo A — arc throw (90 s)

- "Two phones, placed a minute ago, no rig. They looked at the laptop once."
- Drop the ball from shoulder height → point at the screen: **g = 9.8**. "That's the phones
  measuring gravity. Everything you see next is the same math."
- Underhand lob. Screen: 3D arc, release speed, launch angle, apex height.
- Second lob, harder. Numbers move accordingly.

## Demo B — wall bounce (90 s)

- Throw at the wall, catch the return.
- Screen: two arcs split at the impact; speed in → out; impact point on the wall; restitution;
  **g fitted on both legs independently**.
- "Hawk-Eye's job is the bounce point. That's it, from two phones."

## Slides (6)

1. Title + one-line claim.
2. Pros have Hawk-Eye / TrackMan. Amateurs on a court have single-phone apps that need painted
   lines. On a lawn: nothing. (2×2: known geometry vs anywhere × one camera vs multi-view.)
3. Why one camera can't (depth), why two can (rays intersect), what "look at the laptop once" does
   (intrinsics + extrinsics, one shared frame).
4. Pipeline: phones (browser) → detections → Mac → rays → intersect → segments → fits → physics.
5. Accuracy: `g = 9.79 ± 0.15 (n=10)`, residual ~2 cm; chart: error vs number of phones / angle.
6. Next: N phones in the crowd (same math, each phone adds rays); same engine on a sidewalk for
   car speeds.

## Judge Q&A

- **Why two phones?** One camera has no depth. Single-phone apps cheat with known geometry (court
  lines, hoop size). Two views make depth a geometry problem. We need no field markings.
- **Why not a radar gun?** Speed only, only head-on, no trajectory, no bounce, no arc.
- **Does this exist?** For bodies: Uplift Capture (two iPhones on tripods, calibration target,
  cloud). For balls: single-phone apps needing court lines; a 2018 Stanford class project with two
  iPhones got 0.5 m error and needed court landmarks; Maiden AI holds patents, ships single-phone.
  Nobody ships two phones, anywhere, live, in a browser.
- **Why a web page and not an app?** Because it works on any phone in the room in ten seconds —
  that is the whole point of "every spectator's phone can join". (Also true: no App Store needed.)
- **Accuracy?** Depth resolution a few cm at 10 m with a 3 m baseline; speed ~2–3% after sync.
  Degrades with distance² and short baselines.
- **Spin?** Not in v1.
- **Sync?** HTTP min-RTT ping, then refined by minimizing triangulation residual over ±80 ms.
- **What if the ball leaves one camera's view?** Not triangulated for that span; with 3+ phones it
  would be — the N-phone point.
- **Why a checkerboard and not ARKit?** Works on every phone, including ones a judge is holding.
  Deterministic, one photo per phone.

## If the live demo fails

Play Sunday morning's backup video, say "here is this morning's run", keep going.
Do not debug on stage.
