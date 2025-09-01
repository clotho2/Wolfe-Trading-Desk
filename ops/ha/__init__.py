# path: ops/ha/__init__.py
from .leader import RedisLeaderElector, LeaderStatus, set_leader, get_leader


# path: ops/dashboard/app.py (updated with HA endpoints + mode header)
from __future__ import annotations

from typing import Optional

from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.responses import JSONResponse

from config.settings import ExecutorMode, settings
from engine.timebox import now_prague, prague_reset_countdown
from ops.audit.immutable_audit import append_event
from ops.ha.leader import get_leader

app = FastAPI(title="WolfeDesk v0.4.3 Dashboard")


def require_token(authorization: Optional[str] = Header(None)):
    token = (authorization or "").removeprefix("Bearer ").strip()
    if token != settings.DASH_TOKEN:
        raise HTTPException(status_code=401, detail="Unauthorized")
    return True


@app.middleware("http")
async def mode_header(request, call_next):  # type: ignore[no-untyped-def]
    response = await call_next(request)
    response.headers["X-Wolfe-Mode"] = settings.EXECUTOR_MODE.value
    return response


class KillConfirm(BaseModel := __import__("pydantic").BaseModel):
    confirm: bool


class AckConfirm(BaseModel := __import__("pydantic").BaseModel):
    confirm: bool


@app.get("/health")
def health():
    return {"status": "ok", "mode": settings.EXECUTOR_MODE.value}


@app.get("/snapshot", dependencies=[Depends(require_token)])
def snapshot():
    np = now_prague()
    return {
        "prague_now": np.isoformat(),
        "reset_in_seconds": int(prague_reset_countdown(np).total_seconds()),
        "mode": settings.EXECUTOR_MODE.value,
    }


@app.post("/kill", dependencies=[Depends(require_token)])
def kill(payload: KillConfirm):
    if not payload.confirm:
        raise HTTPException(status_code=400, detail="Confirmation required")
    evt = {
        "evt": "KILL_ALL",
        "payload": {"mode": settings.EXECUTOR_MODE.value, "simulated": settings.EXECUTOR_MODE != ExecutorMode.LIVE},
    }
    append_event(evt)
    return JSONResponse({"status": "ok", "message": "Kill issued", "simulated": settings.EXECUTOR_MODE != ExecutorMode.LIVE})


@app.get("/ha/status", dependencies=[Depends(require_token)])
def ha_status():
    leader = get_leader()
    if not leader:
        raise HTTPException(status_code=503, detail="Leader service not running")
    st = leader.status()
    return {
        "is_leader": st.is_leader,
        "fencing_token": st.fencing_token,
        "lockdown_active": st.lockdown_active,
        "last_heartbeat_ts": st.last_heartbeat_ts,
    }


@app.post("/ha/ack", dependencies=[Depends(require_token)])
def ha_ack(payload: AckConfirm):
    if not payload.confirm:
        raise HTTPException(status_code=400, detail="Confirmation required")
    leader = get_leader()
    if not leader:
        raise HTTPException(status_code=503, detail="Leader service not running")
    leader.human_ack()
    append_event({"evt": "HA_HUMAN_ACK", "payload": {"node": "local"}})
    return {"status": "ok", "lockdown_active": leader.status().lockdown_active}
