# path: ops/dashboard/app.py (startup wiring + /ha/status + mode header)
from __future__ import annotations

from typing import Optional

from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from config.settings import ExecutorMode, Settings, settings
from engine.timebox import now_prague, prague_reset_countdown
from ops.audit.immutable_audit import append_event
from ops.ha.bootstrap import start_ha, status as ha_status

app = FastAPI(title="WolfeDesk v0.4.3 Dashboard")


@app.on_event("startup")
async def _startup():
    await start_ha(app, Settings())


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


class KillConfirm(BaseModel):
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


@app.get("/ha/status", dependencies=[Depends(require_token)])
def ha_status_route():
    return ha_status()


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
