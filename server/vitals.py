"""Signal analysis for Vigil: fingertip PPG from a phone camera (torch on), capillary refill, scoring.
Pure numpy. Inputs are lists of [t, R, G, B] per frame (t in seconds, phone clock; only differences matter)."""
from __future__ import annotations

from typing import Dict, List, Optional

import numpy as np


def _bandpass(x: np.ndarray, fs: float, lo: float, hi: float) -> np.ndarray:
    n = len(x)
    F = np.fft.rfft(x - x.mean())
    fr = np.fft.rfftfreq(n, 1 / fs)
    F[(fr < lo) | (fr > hi)] = 0
    return np.fft.irfft(F, n)


def _spectral_peak(x: np.ndarray, fs: float, lo: float, hi: float):
    n = len(x)
    if n < 8:
        return None, 0.0
    F = np.abs(np.fft.rfft((x - x.mean()) * np.hanning(n))) ** 2
    fr = np.fft.rfftfreq(n, 1 / fs)
    band = (fr > lo) & (fr < hi)
    if band.sum() < 3:
        return None, 0.0
    P = F[band]
    i = int(np.argmax(P))
    return float(fr[band][i]), float(P[i] / (np.median(P) + 1e-12))


def _peaks(x: np.ndarray, t: np.ndarray, min_gap_s: float) -> np.ndarray:
    # zero-mean bandpassed signal: every local max above zero is a candidate; the refractory gap removes doubles
    thr = 0.0
    idx = [i for i in range(1, len(x) - 1) if x[i] > x[i - 1] and x[i] >= x[i + 1] and x[i] > thr]
    out = []
    for i in idx:
        if out and t[i] - t[out[-1]] < min_gap_s:
            if x[i] > x[out[-1]]:
                out[-1] = i
        else:
            out.append(i)
    return np.array(out, dtype=int)


def analyze_ppg(frames: List[List[float]]) -> Dict:
    """Fingertip PPG -> HR, RR, HRV, perfusion index, signal quality. Expects >= 10 s at >= 30 fps."""
    a = np.array(sorted(frames), dtype=float)
    if len(a) < 100:
        return {"ok": False, "reason": "too few frames"}
    t = a[:, 0] - a[0, 0]
    dur = float(t[-1])
    fs = len(t) / max(dur, 1e-6)
    R, G = a[:, 1], a[:, 2]
    # torch through the fingertip: red carries the pulse (green is near-saturated dark). Fall back to green if no torch.
    torch = R.mean() > 120 and G.mean() < 60
    raw = R if torch else G
    dc = float(raw.mean())
    if torch and (dc < 60 or dc > 250):
        return {"ok": False, "reason": "finger not covering the lens (mean red %.0f)" % dc}
    # drop first 2 s (exposure settling)
    m = t > 2.0
    t, raw = t[m], raw[m]
    if len(t) < 100:
        return {"ok": False, "reason": "too short after settling"}
    s = -raw  # more blood -> darker -> invert so peaks = systole
    hp = s - np.convolve(s, np.ones(max(3, int(fs))) / max(3, int(fs)), mode="same")
    bp = _bandpass(hp, fs, 0.7, 3.0)
    f_hr, snr = _spectral_peak(hp, fs, 0.7, 3.0)
    pk = _peaks(bp, t, 0.33)
    ibi = np.diff(t[pk]) if len(pk) > 2 else np.array([])
    ibi = ibi[(ibi > 0.33) & (ibi < 1.5)]
    if len(ibi) >= 5:                                  # drop missed/double beats before HRV (>30% off the median)
        med = np.median(ibi)
        ibi = ibi[np.abs(ibi - med) < 0.3 * med]
    hr_pk = 60 / float(np.median(ibi)) if len(ibi) >= 5 else None
    hr = hr_pk if hr_pk is not None else (f_hr * 60 if f_hr else None)
    rmssd = float(np.sqrt(np.mean(np.diff(ibi) ** 2)) * 1000) if len(ibi) >= 6 else None
    sdnn = float(ibi.std() * 1000) if len(ibi) >= 6 else None
    # perfusion index: AC amplitude / DC (%)
    ac = float(np.percentile(bp, 95) - np.percentile(bp, 5))
    pi = ac / dc * 100 if dc > 0 else None
    # respiratory rate: three respiratory modulations, pick the most confident
    rr_candidates = []
    if len(pk) >= 8:
        tp = t[pk]
        amp = bp[pk]                                  # amplitude variation (RIAV)
        freq = np.r_[np.diff(tp), np.diff(tp)[-1]]    # frequency variation (RIFV)
        tu = np.arange(tp[0], tp[-1], 0.25)
        for series in (amp, freq):
            if len(tu) > 40:
                u = np.interp(tu, tp, series)
                f, q = _spectral_peak(u, 4.0, 0.15, 0.6)      # 9–36 breaths/min; below 0.15 Hz is finger-pressure drift
                if f:
                    rr_candidates.append((q, f * 60))
    base = _bandpass(hp, fs, 0.15, 0.6)               # intensity variation (RIIV)
    f, q = _spectral_peak(base, fs, 0.15, 0.6)
    if f:
        rr_candidates.append((q, f * 60))
    rr = None
    if rr_candidates:
        rr_candidates.sort(reverse=True)
        rr = float(rr_candidates[0][1])
    # signal quality: spectral snr + beat regularity
    reg = float(np.clip(1 - (ibi.std() / ibi.mean()) * 2, 0, 1)) if len(ibi) >= 5 else 0.0
    sqi = float(np.clip(min(snr / 20.0, 1.0) * 0.6 + reg * 0.4, 0, 1))
    wave = bp[:: max(1, int(fs // 30))]              # ~30 Hz preview for the UI
    wave = ((wave - wave.min()) / (np.ptp(wave) + 1e-9)).round(3).tolist()
    return {
        "ok": hr is not None and sqi > 0.25,
        "reason": None if hr is not None else "no pulse found",
        "duration_s": round(dur, 1), "fps": round(fs), "torch": bool(torch),
        "hr": round(hr) if hr else None, "hr_spectral": round(f_hr * 60) if f_hr else None,
        "rr": round(rr) if rr else None, "rmssd_ms": round(rmssd) if rmssd else None, "sdnn_ms": round(sdnn) if sdnn else None,
        "pi": round(pi, 2) if pi else None, "sqi": round(sqi, 2), "snr": round(snr, 1), "beats": int(len(ibi)),
        "wave": wave,
    }


def analyze_crt(frames: List[List[float]], release_t: Optional[float] = None) -> Dict:
    """Capillary refill from the same fingertip stream. Protocol: press hard ~5 s (tissue blanches, red rises),
    then relax pressure keeping contact: red falls back as blood returns. Fit an exponential to the recovery."""
    a = np.array(sorted(frames), dtype=float)
    if len(a) < 100:
        return {"ok": False, "reason": "too few frames"}
    t = a[:, 0]; R = a[:, 1]
    fs = len(t) / max(t[-1] - t[0], 1e-6)
    sm = np.convolve(R, np.ones(max(3, int(0.15 * fs))) / max(3, int(0.15 * fs)), mode="same")
    # release = steepest sustained drop; search near the UI marker if given
    d = np.gradient(sm, t)
    if release_t is not None:
        win = (t > release_t - 1.5) & (t < release_t + 2.5)
        if win.sum() > 5:
            d = np.where(win, d, 0)
    i0 = int(np.argmin(d))
    if d[i0] > -1.0:
        return {"ok": False, "reason": "no release detected (press harder, then relax without lifting)"}
    t0 = t[i0]
    seg = (t >= t0) & (t <= t0 + 6)
    ts, ys = t[seg] - t0, sm[seg]
    if len(ts) < 20:
        return {"ok": False, "reason": "not enough data after release"}
    y_inf = float(np.percentile(ys[-max(5, len(ys) // 5):], 50))
    y0 = float(sm[max(0, i0 - int(0.2 * fs))])
    amp = y0 - y_inf
    if amp < 2:
        return {"ok": False, "reason": "blanching too small (press harder)"}
    # time to recover 90% of the drop, read directly from the smoothed curve
    thr90 = y0 - 0.9 * amp
    below = np.where(ys <= thr90)[0]
    t90 = float(ts[below[0]]) if len(below) else None
    # exponential time constant via log-linear fit on the first 70% of recovery
    frac = (ys - y_inf) / amp
    ok = (frac > 0.05) & (frac < 0.95)
    tau = None
    if ok.sum() > 10:
        slope, _ = np.polyfit(ts[ok], np.log(frac[ok]), 1)
        if slope < 0:
            tau = float(-1 / slope)
    return {"ok": t90 is not None, "release_t": float(t0), "crt_s": round(t90, 2) if t90 else None,
            "tau_s": round(tau, 2) if tau else None, "blanch_amp": round(amp, 1),
            "curve": [[round(float(x), 2), round(float(y), 1)] for x, y in zip(ts[:: max(1, int(fs // 20))], ys[:: max(1, int(fs // 20))])]}


RED_FLAGS = {
    "chest pain": "chest pain", "chest pressure": "chest pain", "short of breath": "breathing", "shortness of breath": "breathing",
    "can't breathe": "breathing", "cant breathe": "breathing", "difficulty breathing": "breathing", "stroke": "stroke",
    "face droop": "stroke", "slurred": "stroke", "weakness one side": "stroke", "numb": "stroke",
    "pregnan": "pregnancy", "bleeding": "bleeding", "vomiting blood": "bleeding", "black stool": "bleeding",
    "fainted": "syncope", "passed out": "syncope", "unconscious": "syncope", "seizure": "seizure",
    "allergic": "anaphylaxis", "swelling throat": "anaphylaxis", "overdose": "overdose", "suicid": "psych",
    "infant": "infant", "baby": "infant", "fever": "fever", "confus": "confusion",
}


def complaint_flags(text: str) -> List[str]:
    t = (text or "").lower()
    return sorted({v for k, v in RED_FLAGS.items() if k in t})


def news_points_hr(hr: Optional[float]) -> int:
    if hr is None: return 0
    if hr <= 40: return 3
    if hr <= 50: return 1
    if hr <= 90: return 0
    if hr <= 110: return 1
    if hr <= 130: return 2
    return 3


def news_points_rr(rr: Optional[float]) -> int:
    if rr is None: return 0
    if rr <= 8: return 3
    if rr <= 11: return 1
    if rr <= 20: return 0
    if rr <= 24: return 2
    return 3


def score_patient(p: Dict, now: float) -> Dict:
    """Transparent priority score with reasons. Higher = look sooner."""
    checks = [c for c in p.get("checks", []) if c.get("ok")]
    reasons = []
    score = 0
    last = checks[-1] if checks else None
    first = checks[0] if checks else None
    if last:
        h = news_points_hr(last.get("hr")); r = news_points_rr(last.get("rr"))
        if h: reasons.append(f"HR {last['hr']} (+{h})")
        if r: reasons.append(f"RR {last['rr']} (+{r})")
        score += h + r
        if first is not last and first.get("hr") and last.get("hr") and last["hr"] > 1.2 * first["hr"]:
            score += 1; reasons.append(f"HR up {round((last['hr']/first['hr']-1)*100)}% since arrival (+1)")
        if first is not last and first.get("rr") and last.get("rr") and last["rr"] >= first["rr"] + 4:
            score += 1; reasons.append(f"RR up {last['rr']-first['rr']} since arrival (+1)")
        if last.get("crt_s") is not None and last["crt_s"] > 2.0:
            score += 2; reasons.append(f"capillary refill {last['crt_s']} s (+2)")
        if last.get("pi") is not None and last["pi"] < 0.3:
            score += 1; reasons.append("weak perfusion (+1)")
    flags = p.get("flags", [])
    severe = {"chest pain", "breathing", "stroke", "bleeding", "syncope", "seizure", "anaphylaxis", "overdose", "infant", "confusion"}
    for f in flags:
        if f in severe:
            score += 2; reasons.append(f"complaint: {f} (+2)")
    pain = p.get("pain")
    if pain is not None and pain >= 8:
        score += 1; reasons.append(f"pain {pain}/10 (+1)")
    unreadable = bool(p.get("checks")) and not checks
    due = (now - (last["t"] if last else p.get("joined", now))) > 15 * 60
    if unreadable: reasons.append("last reading unreadable — recheck")
    if due: reasons.append("recheck due")
    return {"score": score, "reasons": reasons, "recheck_due": due, "unreadable": unreadable}
