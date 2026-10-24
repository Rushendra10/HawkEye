# iOS app spec (Rushendra)

Target: one SwiftUI app, `HawkEye`, iOS 17+, **landscape only**. Three screens: Settings,
Calibrate, Live. No storyboard, no CoreData, no frameworks beyond ARKit, AVFoundation (for
nothing in v1), Accelerate (optional), Foundation networking.

## 0. Before writing code (do these while Xcode downloads)

- Both phones: Settings → Privacy & Security → **Developer Mode** → on (reboot).
- Mac: Xcode from the App Store (≈ 8 GB). Open once, let it install components.
- Xcode → Settings → Accounts → add your Apple ID (free). Signing: "Personal Team".
  Limits that do not matter: 7-day profile, max 3 sideloaded apps per phone.
- Bundle id: `com.rushendra.hawkeye` (one id only — free accounts are capped at 10 ids/week).
- Teammate's phone: plug into the Mac, "Trust this computer", Xcode will register it. After first
  run: Settings → General → VPN & Device Management → trust the developer.
- Info.plist keys: `NSCameraUsageDescription`, `NSLocalNetworkUsageDescription`,
  `NSAppTransportSecurity → NSAllowsLocalNetworking = YES` (plain HTTP to the Mac).
- Supported orientations: landscape left + right only.
- Add the marker: Assets → New AR Resource Group → drag `marker/marker.png` → set physical
  width (meters) to the number you measured on the Mac screen. Xcode warns if the image is poor
  for detection; the generated marker passes.

## 1. Settings screen

Fields persisted in `UserDefaults`:
- `serverURL` (e.g. `http://172.20.10.2:8000`) — the Mac's IP on the hotspot
- `deviceID` (`iphone16` / `iphone16promax`)
- `markerWidthM` (default 0.30) — used only to override the asset catalog value at runtime
  (`ARReferenceImage(..., physicalWidth:)`); simpler: keep it in the asset catalog and show it here
  read-only.
- Chroma tolerance (slider, default ±18 in Cb and Cr on 0–255 scale)
- Minimum blob pixels (default 30) and maximum bbox fraction (default 0.15)
- Button: "Sync clock now" (shows last RTT and offset)

## 2. ARKit session (shared by Calibrate and Live)

```swift
let config = ARWorldTrackingConfiguration()
config.worldAlignment = .gravity
if let f = ARWorldTrackingConfiguration.supportedVideoFormats.first(where: { $0.framesPerSecond == 60 }) {
    config.videoFormat = f
}
config.detectionImages = ARReferenceImage.referenceImages(inGroupNamed: "Marker", bundle: nil)
config.maximumNumberOfTrackedImages = 1
session.delegateQueue = DispatchQueue(label: "ar.frames", qos: .userInteractive)
session.run(config)
```

Use `ARSCNView` or `ARView` only for the preview; all logic lives in `ARSessionDelegate`
callbacks. Log `frame.camera.imageResolution` and `frame.camera.intrinsics` once at start — those
numbers go into `/calibration`.

## 3. Calibrate screen

- Shows the camera preview and a status line.
- `session(_:didUpdate anchors:)`: when an `ARImageAnchor` with `isTracked == true` arrives,
  collect its `transform` for 30 consecutive tracked frames; average translation; average rotation
  by picking the sample closest to the mean (keep it simple — do not average quaternions by hand).
  Also capture `frame.camera.transform` at the same moments and average the same way.
- Compute on-phone and display: `T_ac = T_world_anchor.inverse * T_world_camera`, print the
  translation `(x, y, z)` with two decimals. This is the number GATE 1 uses by hand if the server
  is not up yet.
- Status: `SEARCHING` → `LOCKING (n/30)` → `LOCKED`. A "Lock & send" button POSTs `/calibration`
  (`docs/API.md`) and freezes the stored transforms. A "Re-lock" button clears.
- After LOCKED the phone **must not be moved**. Put a big red banner if ARKit reports the camera
  moved more than 2 cm from the locked pose (`distance(frame.camera.transform.translation,
  lockedCameraTranslation) > 0.02`).

Placement procedure (also in DEMO.md): place both phones first, then put the Mac with the marker
where both can see it (≈ 1.5–2.5 m from each, roughly facing both), wait for both LOCKED, send
from both, then take the Mac away. Keep ARKit running.

## 4. Live screen (detection)

Per `session(_:didUpdate frame:)`, on the AR queue:

1. `let pb = frame.capturedImage` — `kCVPixelFormatType_420YpCbCr8BiPlanarFullRange`.
   Plane 0 = Y (full res), plane 1 = interleaved CbCr (half res). Lock base address, read plane 1.
2. For each CbCr pixel (half-res grid, stride = bytesPerRow of plane 1): `inRange =
   |cb - cb0| <= tol && |cr - cr0| <= tol` where `(cb0, cr0)` is the sampled ball chroma.
   Accumulate `count`, `sumX`, `sumY`, `minX/maxX/minY/maxY`. Plain Swift loop over
   `UnsafeMutablePointer<UInt8>` is fast enough (≈ 690k pixels; aim < 6 ms). Do **not** create
   CIImages or UIImages per frame.
3. Accept if `count >= minBlobPixels` and bbox width/height < `maxBBoxFraction * dimension`.
   Centroid in full-res pixels: `u = 2 * sumX / count`, `v = 2 * sumY / count`; bbox ×2 too.
4. Append `{t: frame.timestamp, u, v, n: count, w, h}` to a buffer. Every 0.5 s, POST the buffer
   (possibly empty) to `/detections` with the current `clock_offset`. Fire-and-forget
   `URLSession.shared.dataTask`; drop on failure; never block the AR queue on networking.
5. UI (main thread, throttled to ~10 Hz): `n`, `u`, `v`, fps, server alive dot, and a small square
   drawn over the preview at the centroid (optional; the numbers are enough for development).

Optional improvement if the background has ball-colored stuff: require motion — keep the previous
frame's in-range mask count per 16×16 cell and ignore cells that were in-range for > 1 s. Only do
this if it is actually needed on site.

**Sample ball button:** crosshair at the preview center. Hold the ball there, tap. Read the CbCr at
the buffer center (half-res coordinates `(w/2, h/2)`), average a 9×9 patch, store `(cb0, cr0)`.
Show the sampled color as a swatch so you can see it is sane. A yellow tennis ball under indoor
light is roughly Cb ≈ 60–90, Cr ≈ 130–150; orange is Cb ≈ 90–110, Cr ≈ 170–200. Adjust tolerance
until the count is stable with the ball at 4 m and zero without it.

## 5. Clock sync

At launch and every 60 s (and on the Settings button):

```swift
var best = (rtt: Double.infinity, offset: 0.0)
for _ in 0..<30 {
    let t0 = CACurrentMediaTime()
    let serverTime = try await GET /time          // parse JSON
    let t1 = CACurrentMediaTime()
    let rtt = t1 - t0
    if rtt < best.rtt { best = (rtt, serverTime - (t0 + rtt/2)) }
}
clockOffset = best.offset
```

Show `best.rtt` in ms on Settings. Over a phone hotspot expect 5–30 ms RTT; the min-RTT sample is
typically accurate to 2–3 ms. The solver refines the rest.

## 6. Order of work (hard part first)

1. Project builds and runs on both phones (camera preview only). **Stop here until this works.**
2. Calibrate screen: marker lock, on-screen `(x, y, z)`. Place both phones 3 m apart, lock both,
   compute the distance by hand, tape-measure the real distance. **GATE 1.**
3. Live screen: detection numbers on screen, ball at 1 m, then at 4 m, then thrown.
4. Clock sync + POSTs. Watch the server log fill up.
5. Drop test with the teammate's solver. **GATE 2.**
6. Then and only then: tolerance tuning, movement banner, settings polish, re-lock flow.
7. Stretch (after GATE 3): 240 fps via AVFoundation (stop ARKit after lock, start
   `AVCaptureSession` with a `1920×1080 @ 240` format, `isCameraIntrinsicMatrixDeliveryEnabled`
   on the connection, send the new intrinsics in a fresh `/calibration` with the same pose).
   Or an AR trail drawn in the preview from `/latest`. Pick one, not both.

## 7. Known gotchas

- `capturedImage` is landscape in sensor orientation regardless of how the phone is held; the
  intrinsics match that buffer. Do all math on the raw buffer. Only the preview needs rotating.
- ARKit may re-detect the image and update the anchor slightly for a few seconds; that is why we
  average 30 tracked frames and then freeze.
- Image detection needs the marker to be reasonably large in frame: a 30 cm marker at 2 m is fine;
  at 4 m it may not lock. Bring the Mac closer to each phone **only if the Mac stays in one spot
  for both locks** (both phones must see it at the same place). Practical: put the Mac at the middle
  between the phones, slightly toward the throwing volume.
- 60 fps ARKit + a tight pixel loop keeps the phone warm; plug in during rehearsals.
- If `supportedVideoFormats` has no 60 fps entry on a device, fall back to 30 fps and tell the
  teammate (the solver does not care; the throws are just coarser).
- Free-account builds expire after 7 days — irrelevant, but rebuild Sunday morning anyway so the
  demo build is fresh and both phones have the same version.
