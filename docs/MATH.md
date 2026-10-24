# MATH — the solver, step by step

Pure numpy/scipy. Must run offline on JSONL logs (`python solver.py data/<session>/`) and inside
the server on every new batch. Keep functions small and testable; the simulator (§9) is the test.

## 1. Cameras into one frame

For each device with a calibration:

```
T_ac = inv(T_world_anchor) @ T_world_camera         # 4x4, camera -> anchor frame
C    = T_ac[:3, 3]                                   # camera center in anchor frame
R    = T_ac[:3, :3]                                  # camera -> anchor rotation
up   = normalize(T_world_anchor[:3, :3].T @ [0, 1, 0])   # ARKit gravity-up in anchor frame
```

Average `up` over the two devices (they should agree within a degree or two; log the angle).
`baseline_m = |C_A - C_B|` → returned by `/calibration` for GATE 1.

## 2. Pixel → ray

```
d_cam   = normalize([(u - cx)/fx, -(v - cy)/fy, -1.0])
d_world = R @ d_cam                                  # unit direction in anchor frame
ray     = (C, d_world)
```

## 3. Event (throw) detection

Per device, convert `t_server = t + clock_offset`. Keep a rolling buffer of (t_server, u, v, n).
A **throw event** is a window where both devices have ≥ 15 detections within any 1.5 s span and the
2D displacement over the window exceeds 80 px (something actually moved). Extend the window while
detections keep arriving (gap < 0.25 s). Solve once the window has been quiet for 0.5 s.
Drop detections with `n` below a threshold (default 30 px) or `w, h` > 15% of the image.

## 4. Time-offset refinement (Δt)

Clock sync by HTTP is good to a few ms; a frame at 60 fps is 16.7 ms, so this is usually fine,
but do it anyway because it is cheap and it catches a bad sync:

```
for dt in arange(-0.060, 0.060, 0.001):            # seconds
    for each time t in device A's track (resampled to its own frame times):
        pA = A(t)                                    # (u,v) from A
        pB = B_interp(t + dt)                        # linear interpolation of B's (u,v)
        X, resid = triangulate(rayA(pA), rayB(pB))   # §5
    cost(dt) = median(resid)
dt* = argmin cost
```

Apply `dt*` to device B. Report `dt_refined_ms`. If `cost(dt*)` is still > 5 cm, the calibration is
off (see §8).

## 5. Triangulation (two rays, closed form)

Rays `(C1, d1)`, `(C2, d2)`, unit directions. Closest points:

```
w0 = C1 - C2
a = d1·d1 = 1; b = d1·d2; c = d2·d2 = 1; d = d1·w0; e = d2·w0
den = a*c - b*b                       # ~0 when rays are parallel -> reject
s = (b*e - c*d) / den
t = (a*e - b*d) / den
P1 = C1 + s*d1;  P2 = C2 + t*d2
X = (P1 + P2) / 2
resid = |P1 - P2|                    # ray-ray distance; reject if > 0.10 m
```

Also reject if `s < 0.3` or `t < 0.3` (point behind or inside a camera). Output a list of
`(t_server, X, resid)`.

For N > 2 cameras (stretch / slides chart): least squares `X = argmin Σ |(I - d_i d_iᵀ)(X - C_i)|²`,
closed form: `X = (Σ (I - d_i d_iᵀ))⁻¹ Σ (I - d_i d_iᵀ) C_i`.

## 6. Bounce segmentation

Compute velocity by central differences on the 3D points (after a light 3-point median filter).
A bounce is a frame where the angle between consecutive velocity vectors exceeds 60° **and** speed
is above 1 m/s (filters the apex, where the turn is slow and gentle). Split the point list there.
Expect: Demo A → 1 segment; Demo B → 2 segments; a floor bounce adds more. Discard segments with
< 8 points.

## 7. Parabola fit and metrics (per segment)

Model `p(t) = p0 + v0 (t - t0) + ½ a (t - t0)²`, with `t0` the segment's first time. Linear least
squares in the 9 unknowns (3 per axis, solved per axis independently). Then a RANSAC-lite pass:
drop points with residual > 3× median, refit once.

Metrics:
- `g_fit = |a|`; `g_dir_err_deg = angle(-a, up)`  ← the honesty numbers
- `rms_residual_cm`
- `speed_mps = |v0|` (release speed for the first segment, post-bounce speed for the second)
- `launch_angle_deg = asin((v0·up)/|v0|)`
- `apex_height_m = max over fitted curve of (p·up) - (first point·up)`
- `range_m = horizontal distance between first and last fitted point`
- `flight_time_s`

For reporting, **do not force `g` = 9.8 in the fit**. The point of the demo is that the fit finds it.

### Bounce (Demo B)
- Impact point: where the two segment fits are closest around the split time (evaluate both fits
  at the split time, average).
- `v_in` = segment 1 fitted velocity at the split time; `v_out` = segment 2 fitted velocity at the
  split time.
- Normal: `n = normalize(v_out - v_in)` (exact for a frictionless bounce; good enough here).
- `restitution = |v_out·n| / |v_in·n|`. Also report `speed_in_mps`, `speed_out_mps`.

### Drop classification (for GATE 3 statistics)
A throw whose first segment has horizontal speed < 0.5 m/s and `v0·up` > -0.5 m/s is a "drop".
Keep running `g_mean`, `g_std`, `count` over drops.

## 8. When `g` comes out wrong — the sign table

| Symptom | Likely cause | Fix |
|---|---|---|
| `g` ≈ 9.8 but points **up** | image `v` sign in pixel→ray | flip the `-` on `(v - cy)` |
| `g` ≈ 9.8 but points **sideways** (±90°) | up vector taken in the wrong frame | recompute `up = R_world_anchor^T @ [0,1,0]`, check you used anchor, not camera |
| `g` ≈ 9.8 but mirrored throw direction | camera forward sign | use `-1` for z in `d_cam` (ARKit looks down −z) |
| `g` is 2× or ½ of 9.8 | timestamps in ms vs s, or using one phone's clock for the other | check units; apply `clock_offset` per device |
| `g` right, residuals > 5 cm | calibration off (baseline wrong) | redo GATE 1; check `anchor_physical_width_m` |
| `g` noisy run to run | poor sync | widen Δt search; check RTT during sync |

## 9. Simulator (`server/simulate.py`) — build this first

- Two virtual cameras: positions ~3 m apart, 1.2 m high, each yawed ~30° toward the center,
  `fx = fy = 1450`, `cx = 960`, `cy = 720`, image `1920×1440`.
- A random throw: `p0` near one side, `v0` 5–9 m/s at 30–50° elevation, gravity `9.81` down;
  optional wall plane at x = 2.5 m with restitution 0.7 (reflect normal velocity component).
- Sample at 60 fps per camera, with independent random time offsets (±30 ms) and jitter, project
  to pixels with the **same** conventions as §2 inverted, add Gaussian pixel noise (σ = 1.5 px),
  occasionally drop frames.
- Emit `/calibration` and `/detections` payloads exactly as `docs/API.md`, and either POST them to
  a running server or write them as JSONL.
- Test: the solver recovers `g` within ±0.2 and the wall restitution within ±0.05 on the synthetic
  data. If the simulator and solver disagree, one of them has a convention bug — fix before touching
  real data.
- Later (slides): sweep number of cameras N = 2..8 and the angle between them; plot median 3D
  error. This is the "every spectator's phone makes it sharper" chart.

## 10. Dashboard (`server/static/index.html`)

One page, Plotly from CDN, polls `/latest` every second. Shows:
- 3D plot: camera positions as cones/markers with forward arrows, raw triangulated points, fitted
  curve per segment, impact point marker, `up` as the vertical axis.
- Big-number panel: speed, launch angle, apex, flight time, and in a highlighted box
  `g = 9.78 m/s² (dir err 1.9°)`.
- For Demo B: speed in / out, restitution.
- Small status line: both cameras alive (age < 2 s), baseline, Δt refined, drops `g_mean ± g_std (n)`.
- A "Reset" button → `POST /reset`.

Make it readable from the back of a theatre: dark background, large fonts, one throw at a time.
