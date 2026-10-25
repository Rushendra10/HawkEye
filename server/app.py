"""Vigil server: patients' phones post fingertip-PPG measurements; the nurse board ranks everyone in the room.
Run (TLS, phones):  uvicorn app:app --host 0.0.0.0 --port 8443 --ssl-certfile certs/cert.pem --ssl-keyfile certs/key.pem
"""
from __future__ import annotations

import json
import os
import secrets
import time
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

import vitals

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data", time.strftime("%Y%m%d_%H%M%S"))
os.makedirs(DATA, exist_ok=True)

app = FastAPI(title="Vigil")
from fastapi.middleware.cors import CORSMiddleware  # noqa: E402
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
app.mount("/static", StaticFiles(directory=os.path.join(HERE, "static")), name="static")

PATIENTS: Dict[str, Dict[str, Any]] = {}
ROOM: Dict[str, Dict[str, Any]] = {}      # breathing rates from the room camera, keyed by seat label


def log(name: str, obj: Dict[str, Any]) -> None:
    with open(os.path.join(DATA, name + ".jsonl"), "a") as f:
        f.write(json.dumps({**obj, "received_at": time.time()}) + "\n")


@app.get("/")
def index():
    return FileResponse(os.path.join(HERE, "static", "board.html"))


@app.get("/time")
def get_time():
    return {"server_time": time.time()}


@app.get("/qr.png")
def qr_png(request: Request):
    """QR for the patient page, pointing at whatever host the board was opened on (hotspot IP)."""
    import io
    import qrcode
    host = request.headers.get("host", "172.20.10.2:8443").split(":")[0]
    if host in ("localhost", "127.0.0.1"):            # board opened on the Mac itself: phones need the hotspot IP
        host = os.environ.get("VIGIL_HOST", "172.20.10.2")
    url = f"https://{host}:8443/static/patient.html"
    img = qrcode.make(url, box_size=6, border=1)
    buf = io.BytesIO(); img.save(buf, format="PNG")
    from fastapi.responses import Response
    return Response(content=buf.getvalue(), media_type="image/png", headers={"X-Url": url})


class Join(BaseModel):
    name: str
    age: Optional[int] = None
    complaint: str = ""
    pain: Optional[int] = None


@app.post("/join")
def join(j: Join):
    pid = secrets.token_hex(3)
    PATIENTS[pid] = {"id": pid, "name": j.name[:24], "age": j.age, "complaint": j.complaint[:200], "pain": j.pain,
                     "flags": vitals.complaint_flags(j.complaint), "joined": time.time(), "checks": [],
                     "recheck_requested": False, "glow": None}
    log("join", {"id": pid, **j.dict()})
    return {"id": pid, "flags": PATIENTS[pid]["flags"]}


class Measure(BaseModel):
    id: str
    frames: List[List[float]]          # [t, R, G, B]
    crt_frames: Optional[List[List[float]]] = None
    crt_release_t: Optional[float] = None


@app.post("/measure")
def measure(m: Measure):
    p = PATIENTS.get(m.id)
    if not p:
        return JSONResponse({"ok": False, "reason": "unknown patient"}, status_code=404)
    res = vitals.analyze_ppg(m.frames)
    crt = vitals.analyze_crt(m.crt_frames, m.crt_release_t) if m.crt_frames else None
    check = {"t": time.time(), **{k: v for k, v in res.items() if k != "wave"}}
    if crt and crt.get("ok"):
        check["crt_s"] = crt["crt_s"]; check["crt_tau_s"] = crt.get("tau_s")
    p["checks"].append(check)
    p["recheck_requested"] = False
    log("measure", {"id": m.id, "n_frames": len(m.frames), "result": check, "crt": crt and {k: v for k, v in crt.items() if k != "curve"}})
    # keep raw frames for offline work
    with open(os.path.join(DATA, f"raw_{m.id}_{int(time.time())}.json"), "w") as f:
        json.dump({"frames": m.frames, "crt_frames": m.crt_frames, "crt_release_t": m.crt_release_t}, f)
    return {"ok": res.get("ok", False), "result": res, "crt": crt, "score": vitals.score_patient(p, time.time())}


@app.get("/me/{pid}")
def me(pid: str):
    p = PATIENTS.get(pid)
    if not p:
        return JSONResponse({"ok": False}, status_code=404)
    last = p["checks"][-1] if p["checks"] else None
    return {"ok": True, "name": p["name"], "recheck_requested": p["recheck_requested"], "glow": p["glow"],
            "last_check_t": last["t"] if last else None, "last": last, "score": vitals.score_patient(p, time.time())}


@app.post("/recheck/{pid}")
def recheck(pid: str):
    if pid in PATIENTS:
        PATIENTS[pid]["recheck_requested"] = True
    return {"ok": pid in PATIENTS}


@app.post("/glow/{pid}")
def glow(pid: str, color: Optional[str] = None):
    if pid in PATIENTS:
        PATIENTS[pid]["glow"] = None if PATIENTS[pid]["glow"] else (color or "#ff7a00")
    return {"ok": True, "glow": PATIENTS.get(pid, {}).get("glow")}


@app.post("/seen/{pid}")
def seen(pid: str):
    """Nurse took the patient in: remove from the board."""
    PATIENTS.pop(pid, None)
    return {"ok": True}


class RoomUpdate(BaseModel):
    seats: Dict[str, Dict[str, Any]]    # label -> {rr, snr, amp, t}


@app.post("/room")
def room(r: RoomUpdate):
    ROOM.update(r.seats)
    return {"ok": True}


@app.get("/patients")
def patients():
    now = time.time()
    out = []
    for p in PATIENTS.values():
        sc = vitals.score_patient(p, now)
        ok_checks = [c for c in p["checks"] if c.get("ok")]
        last = p["checks"][-1] if p["checks"] else None
        out.append({"id": p["id"], "name": p["name"], "age": p["age"], "complaint": p["complaint"], "pain": p["pain"], "flags": p["flags"],
                    "joined": p["joined"], "last": last, "n_checks": len(p["checks"]), "recheck_requested": p["recheck_requested"],
                    "glow": p["glow"], "hr_series": [[c["t"], c.get("hr")] for c in ok_checks], "rr_series": [[c["t"], c.get("rr")] for c in ok_checks],
                    **sc})
    out.sort(key=lambda x: (-x["score"], -(now - (x["last"]["t"] if x["last"] else x["joined"]))))
    return {"server_time": now, "patients": out, "room": ROOM}


@app.post("/reset")
def reset():
    PATIENTS.clear(); ROOM.clear()
    return {"ok": True}
