# Demo — setup checklist, scripts, judge Q&A

## Setup checklist (10 minutes, do it in this order every time)

1. Hotspot on. Mac, both phones, dashboard laptop joined. Note the Mac's IP.
2. Mac: `cd server && source .venv/bin/activate && uvicorn app:app --host 0.0.0.0 --port 8000`.
   Open `http://<mac-ip>:8000/` on the projector. Press Reset.
3. Place the phones: landscape, resting against bottles, ~3 m apart, each angled ~30° toward the
   center of the throwing volume, lens height ~0.6–1.2 m. Both should see the whole arc and the
   wall (Demo B). Do not touch them again.
4. Both phones: open app → Calibrate. Put the Mac (marker fullscreen, `marker/marker.html`)
   ~2 m from each phone, screen facing both. Wait for LOCKED on both. "Lock & send" on both.
   Dashboard shows both cameras and the baseline. Sanity: baseline ≈ tape measure.
5. Remove the Mac. Both phones → Live. Dashboard shows both cameras alive.
6. Hold the ball at center → Sample ball (if lighting changed since last time).
7. Drop test once. `g` on screen. If not within 9.8 ± 0.5, re-lock (step 4) before demoing.
8. Ball #2 in your pocket.

## Demo A — arc throw (90 s)

- "Two phones, placed ten seconds ago, no calibration rig."
- Drop the ball from shoulder height → point at the screen: **g = 9.8**. "That's the phones
  measuring gravity. Everything you see next is the same math."
- Underhand lob across the volume. Screen: 3D arc, release speed, launch angle, apex height.
- Second lob, harder. Numbers change accordingly.

## Demo B — wall bounce (90 s)

- Throw at the wall, catch the return.
- Screen: two arcs, split at the impact; speed in → speed out; impact point on the wall;
  restitution; **g fitted on both legs independently**.
- "Hawk-Eye's job is the bounce point. That's it, from two phones."

## Slides (6, no more)

1. Title + one-line claim.
2. Pros have Hawk-Eye / TrackMan. Amateurs on a court have single-phone apps that need painted
   lines. On a lawn: nothing. (2×2: known geometry vs anywhere × one camera vs multi-view.)
3. Why one camera can't do it (depth), why two can (rays intersect), why ARKit makes it free
   (pose + intrinsics, marker as shared frame).
4. Pipeline diagram: phones → detections → Mac → rays → intersect → segments → fits → physics.
5. Accuracy: `g = 9.79 ± 0.15 (n=20)`, residual ~2 cm; chart: error vs number of phones / angle
   ("every spectator's phone makes it sharper").
6. What's next: N phones in the crowd; same engine on a sidewalk for car speeds (Vision Zero).

## Judge Q&A (have these cold)

- **Why two phones, one is enough?** One camera has no depth. Single-phone apps cheat with known
  geometry (court lines, hoop size). We need neither. Two views make depth a geometry problem.
- **Why not a radar gun?** Speed only, only when the ball flies straight at it, no trajectory, no
  bounce, no arc. We give the whole flight.
- **Does this exist?** For bodies, yes (Uplift Capture: two iPhones on tripods, calibration, cloud).
  For balls: single-phone apps that need court lines; a 2018 Stanford class project with two
  iPhones got 0.5 m error and needed court landmarks; Maiden AI holds patents but ships single-phone.
  Nobody ships two phones, dropped anywhere, live.
- **Accuracy?** Depth resolution a few cm at 10 m with a 3 m baseline; speed ~2–3% after sync.
  Degrades with distance² and short baselines; the app nags you to spread the phones.
- **Spin?** Not in v1. Needs ball texture at high resolution.
- **Sync?** HTTP min-RTT ping, then refined by minimizing triangulation residual over ±60 ms.
- **What if the ball leaves one camera's view?** That segment is not triangulated; with 3+ phones
  it would be. That is the N-phone point.
- **Why ARKit image marker and not collaborative sessions?** One-shot, deterministic, both phones
  only need to see the same image once. Less to go wrong on stage.
- **Could spectators' phones join?** Same math; each extra phone adds rays. Shown in the chart.
  Not live today (free developer account, no App Store build).

## If the live demo fails

Play the backup video of a clean run (recorded Sunday morning), say "here is this morning's run",
keep going. Do not debug on stage.
