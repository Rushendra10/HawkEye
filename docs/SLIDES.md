# Vigil — slides (6) — paste into Google Slides / Keynote

## 1 · Title
**Vigil — the waiting room gets a monitor**
Social Hack 2026 · Connect & Intersect · Rushendra + [teammate]
*Sub: every phone in the waiting room becomes the monitor that notices.*

## 2 · The gap nobody staffs
- Triage is a **snapshot**: 2 minutes at arrival → "stable, wait."
- Then you sit for hours. Guidelines: re-check waiting patients every 1–2 h. Under load, it's skipped.
- People deteriorate silently in waiting rooms — early sepsis, bleeding, evolving heart attacks — and some die there. 2–10% leave without being seen.
- **We don't prevent deterioration. We shorten how long it goes unnoticed.**

## 3 · What a phone can measure (physics, not AI)
- Fingertip on the camera, flash on → blood absorbs light → pulse-oximeter-grade waveform at 120 fps.
  → **heart rate, breathing rate** (respiratory modulation of the pulse), **HRV**, **perfusion**.
- Press, then relax → **capillary refill time** — the sepsis/shock sign nurses check by pressing a nail — measured in ms.
- A room camera → chest motion → **breathing rate for everyone in view**, continuously, contactless.
- *(Show: the real waveform; HR 72 vs. a counted pulse; refill curve.)*

## 4 · The board
- Every patient: score, vitals, trend since arrival, and **why** in plain words.
- Transparent NEWS-style rule: HR + RR points · +1 trend bumps · +2 refill > 2 s · +2 red-flag complaint · +1 pain ≥ 8. Sorted by score, then longest since last check.
- Re-check (patient's phone asks) · Find (patient's phone glows) · Seen.
- *(Live demo here.)*

## 5 · Honest limits · what we built first
- A reassessment aid, not a diagnosis. No SpO2, no BP number. Only what a pulse can show. Needs the patient to do a 30-second check (prompted every 15 min).
- First we built **HawkEye**: two phones → 3D ball tracking. Calibration worked (0.3 px); the per-use setup didn't earn its demo. Code in `legacy_hawkeye/`. We kept the stack (Safari pages → Mac → board) and pointed it at something that matters.

## 6 · What's next (designed, not built)
- **Two-phone transit-time station**: forehead + finger, synced to the ms → pulse transit time, the signal behind cuffless blood pressure; catches the shock pattern (HR up, transit time up).
- **Deterioration model** on PhysioNet 2019 (40k ICU stays, hourly vitals) → risk from trajectories, shown next to the rule, never instead of it.
- Pilot: one waiting room, one nurse, BYOD + a few loaner phones.
