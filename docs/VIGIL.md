# Vigil , the waiting room gets a monitor

**We pivoted (Sat ~20:30).** HawkEye (two-phone 3D ball tracking) worked through calibration but the
per-use setup was too heavy to demo well. Everything built for it lives in `legacy_hawkeye/` , keep it,
it is part of the story. The project is now **Vigil**. Same stack: Safari web pages on phones → FastAPI
on the Mac over HTTPS → a browser dashboard.

## One paragraph

Triage is a snapshot at arrival. Waiting is where people get worse unseen , guidelines say re-check
waiting patients every 1–2 h, and understaffed ERs miss it. Vigil turns every phone in the waiting
room into the monitor that notices: scan a QR, put a fingertip on the camera for 30 s (flash on) →
heart rate, breathing rate, HRV, perfusion, and a capillary-refill test (press, relax) → the nurse's
board ranks everyone by a transparent NEWS-style score plus *trend since arrival*, asks for re-checks,
and can make a patient's phone glow to find them. A room camera counts everyone's breathing between
checks. Honest claims only: catch deterioration sooner, not prevent it; a reassessment aid, not a
diagnostic; no SpO2, no BP number.

## What exists now (Sat 21:30) , `server/`

- `app.py` , FastAPI. `POST /join`, `POST /measure` (raw [t,R,G,B] frames + CRT frames), `GET /me/{id}`,
  `POST /recheck/{id}`, `POST /glow/{id}`, `POST /seen/{id}`, `GET /patients`, `POST /room`, `POST /reset`.
  Run: `uvicorn app:app --host 0.0.0.0 --port 8443 --ssl-certfile certs/cert.pem --ssl-keyfile certs/key.pem`
- `vitals.py` , PPG analysis (HR, RR from respiratory modulation, RMSSD/SDNN, perfusion index, SQI),
  capillary refill (exponential recovery after release), complaint red flags, NEWS-style score with reasons.
  Verified on real data: HR 72 (contact finger, 120 fps, SNR 155).
- `static/patient.html` , join → 20 s pulse check with live waveform → press/relax refill test → results →
  15-min countdown; polls `/me` for nurse re-check requests and "find me" glow.
- `static/board.html` , nurse board: ranked table, sparklines, reasons, Re-check / Find / Seen, QR to join,
  room-breathing panel (reads `/patients.room`).
- `static/breath_test.html` , single-ROI contactless breathing tracker (chest motion, in-browser). Works
  on the Mac webcam. This is the seed for `room.html`.
- `static/vitals_test.html` , the feasibility page (face vs finger). Keep for reference.

## Tasks , teammate (tonight if awake, else Sunday 07:00)

1. **`static/room.html`** , the room camera. Start from `breath_test.html`. Changes:
   - Up to 6 boxes instead of one: tap adds a box (label "seat 1…6"), tap inside a box removes it.
   - Run the same tracker per box (profile shift vs. the frame 0.5 s earlier, sway rejection, leaky integral,
     rate from the 0.1–0.7 Hz spectral peak over the last 24 s). Keep the per-frame loop cheap: boxes at
     128×192 analysis size.
   - Every 2 s `POST /room` with `{ "seats": { "seat 1": { "rr": 14.2, "snr": 6.1, "amp": 1.3, "t": <unix s> }, ... } }`.
     Send `rr: null` when snr < 3 (not confident). The board already renders this panel.
   - Show the rate above each box on the overlay, red if > 24, plus "apnea" if amplitude collapses for > 8 s.
   - Runs on the Mac at `https://localhost:8443/static/room.html` (accept the cert warning, or run
     `mkcert -install` once) or on a phone propped on a stand.
2. **Slides (6)** , `docs/DEMO.md` has the structure; rewrite for Vigil: the waiting-room problem, what we
   measure and how (finger PPG physics, capillary refill, room breathing), the board and score, the honest
   limits, what we built first (HawkEye) and why we switched, what's next (two-phone transit time station,

## Tasks , Rushendra (tonight)

1. End-to-end on both phones: join → measure → board shows the row with HR/RR/refill; Re-check and Find work.
2. Tune `vitals.py` thresholds on your own readings (beats found vs expected, RR plausible, CRT 0.5–1.5 s normal).
3. Demo data: 3–4 friends check in tonight so the board has rows; teammate does 40 squats → re-check →
   row jumps (HR +, RR +, "HR up X% since arrival").
4. Record a backup video of the full flow.

## Sunday

07:00 room.html test in the theatre lighting · 08:00 rehearsals (judges scan QR, finger check, squats,
room breathing, Find) · 09:00 README + slides final · 10:00 submit (form deadline 12:00).

## Demo script (5 min)

1. "Triage is a snapshot. Waiting is where people get worse unseen." (20 s)
2. Judge scans QR, types a complaint, finger on camera, 30 s , their row appears with HR, breathing, HRV,
   refill. "That's a pulse-oximeter-grade waveform from the phone in your pocket." (90 s)
3. Board: ranking, reasons, trend; teammate (checked in earlier) rechecks after squats → jumps to top,
   flagged. Nurse taps Find → her phone glows. (90 s)
4. Room camera: breathing rates over the audience; someone holds their breath → apnea flag. (45 s)
5. Honest limits + what's next. (30 s)
