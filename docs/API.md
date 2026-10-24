# API — the contract between the iOS app and the server

Everything is JSON over plain HTTP. Server listens on `0.0.0.0:8000` on the Mac.
Units: **meters, seconds, radians-free (degrees only in dashboard text)**. Matrices are row-major
nested lists. Phones never send images.

## Conventions (read twice)

- **Time.** Phones timestamp with their own monotonic clock (`ARFrame.timestamp`, same clock as
  `CACurrentMediaTime()`). Every payload carries `clock_offset` so the server can convert:
  `server_time = phone_time + clock_offset`. The phone computes `clock_offset` from `GET /time`
  (see below). The solver additionally refines a small residual offset between the two phones.
- **Pixels.** `(u, v)` are pixel coordinates in ARKit's native `capturedImage` buffer: origin
  top-left, `u` to the right, `v` down, size `image_size = [width, height]` (e.g. `[1920, 1440]`).
  Not view coordinates, not rotated for display.
- **Camera space (ARKit):** `+x` right, `+y` up, `-z` forward (the camera looks down `-z`).
- **Pixel → ray in camera space:** `d = normalize([(u - cx)/fx, -(v - cy)/fy, -1])`.
  (The minus on `v` is because image `v` goes down while camera `y` goes up. If GATE 2 shows `g`
  pointing the wrong way, this sign and the `-1` are the first suspects; see MATH.md §8.)
- **Frames.** Each phone has its own ARKit world frame (gravity-aligned: world `-y` is down).
  Each phone reports `T_world_camera` and `T_world_anchor` (both 4×4, column vectors, i.e.
  `p_world = T · p_local`). The server puts everything into the **anchor frame**:
  `T_anchor_camera = inv(T_world_anchor) · T_world_camera`, and gets "up" in the anchor frame as
  `R_world_anchor^T · [0, 1, 0]`.
- **Anchor frame geometry (FYI).** For an `ARImageAnchor` the image lies in the anchor's x–z plane
  with `+y` pointing out of the image toward the viewer. We do not rely on this; we only use the
  anchor as a shared frame and take "up" from ARKit gravity.

## Endpoints

### `GET /time`
Clock sync. Returns the server's wall clock.

```json
{ "server_time": 1761350400.123456 }
```

Phone procedure (do this at launch and every 60 s): 30 requests in a row; for each, record
`t0 = CACurrentMediaTime()` before sending and `t1` after the response; `rtt = t1 - t0`;
`offset_i = server_time - (t0 + rtt/2)`. Keep the `offset_i` from the request with the **smallest
rtt**. That is `clock_offset`.

### `POST /calibration`
Sent once per phone after the marker lock is stable (and again if the user re-locks).

```json
{
  "device_id": "iphone16",
  "clock_offset": 1761350000.42,
  "image_size": [1920, 1440],
  "intrinsics": [[fx, 0, cx], [0, fy, cy], [0, 0, 1]],
  "T_world_camera": [[r,r,r,tx],[r,r,r,ty],[r,r,r,tz],[0,0,0,1]],
  "T_world_anchor": [[r,r,r,tx],[r,r,r,ty],[r,r,r,tz],[0,0,0,1]],
  "anchor_physical_width_m": 0.30,
  "gravity_world": [0, -1, 0],
  "notes": "optional free text"
}
```

Server: store latest calibration per `device_id`; append to `data/<session>/calibration.jsonl`.
Respond with the camera position in the anchor frame and, if two calibrations exist, the distance
between the two cameras (this is what GATE 1 reads):

```json
{ "ok": true, "camera_position_anchor": [x, y, z], "baseline_m": 2.97 }
```

### `POST /detections`
Sent every ~0.5 s by each phone while in Live mode, **including when empty** (so the server knows
the phone is alive). Only frames where the ball was found are listed.

```json
{
  "device_id": "iphone16",
  "clock_offset": 1761350000.42,
  "frames": [
    { "t": 12345.6789, "u": 812.3, "v": 455.1, "n": 420, "w": 24, "h": 26 },
    { "t": 12345.6956, "u": 818.9, "v": 441.0, "n": 415, "w": 24, "h": 25 }
  ]
}
```

- `t` phone monotonic seconds (ARFrame.timestamp)
- `u, v` blob centroid in capturedImage pixels (full resolution)
- `n` number of pixels in the blob (quality signal); `w, h` bounding box in pixels

Server: append to `data/<session>/detections_<device_id>.jsonl`, keep a rolling in-memory buffer
of the last 60 s per device, and run event detection + solve (MATH.md §3 onward) whenever a new
batch arrives. Respond `{ "ok": true }`.

### `GET /latest`
What the dashboard polls (every 1 s).

```json
{
  "server_time": 1761350400.1,
  "cameras": [
    { "device_id": "iphone16", "position": [x,y,z], "forward": [dx,dy,dz], "age_s": 0.4 }
  ],
  "baseline_m": 2.97,
  "up": [ux, uy, uz],
  "throws": [
    {
      "id": 7,
      "t_start": 1761350380.2,
      "dt_refined_ms": -3.0,
      "segments": [
        {
          "points": [[x, y, z, t], ...],
          "fit": {
            "p0": [x,y,z], "v0": [vx,vy,vz], "a": [ax,ay,az],
            "g_fit": 9.74, "g_dir_err_deg": 2.1, "rms_residual_cm": 1.8,
            "speed_mps": 6.9, "launch_angle_deg": 38.0, "apex_height_m": 1.92,
            "range_m": 3.4, "flight_time_s": 0.81
          }
        }
      ],
      "bounce": {
        "point": [x,y,z], "t": 1761350380.9,
        "speed_in_mps": 6.1, "speed_out_mps": 4.4,
        "normal": [nx,ny,nz], "restitution": 0.72
      }
    }
  ],
  "drops": { "count": 10, "g_mean": 9.79, "g_std": 0.15 }
}
```

`bounce` is null for Demo A. `drops` summarizes throws classified as free drops (near-zero initial
horizontal speed) — this is the GATE 3 statistic.

### `GET /`
Serves `static/index.html` (the dashboard). `GET /static/...` for assets.

## Logging format

One session directory per server start: `data/YYYYMMDD_HHMMSS/`. Every incoming POST body is
appended as one JSON line, with `"received_at": server_time` added. The solver must be runnable
offline from these files: `python solver.py data/<session>/` prints the same JSON as `/latest`.
This is how the teammate develops against real captures without the phones present.

## Session reset

`POST /reset` clears in-memory state (keeps the log files). Used between rehearsal runs.
