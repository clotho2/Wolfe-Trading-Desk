from fastapi import FastAPI, Depends, HTTPException, Header
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Optional
from config.settings import settings, ExecutorMode
from ops.audit.immutable_audit import append_event
from engine.timebox import now_prague, prague_reset_countdown

app = FastAPI(title="WolfeDesk v0.4.3 Dashboard")

def require_token(authorization: Optional[str] = Header(None)):
    token = (authorization or "").removeprefix("Bearer ").strip()
    if token != settings.DASH_TOKEN:
        raise HTTPException(status_code=401, detail="Unauthorized")
    return True

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

@app.post("/kill", dependencies=[Depends(require_token)])
def kill(payload: KillConfirm):
    if not payload.confirm:
        raise HTTPException(status_code=400, detail="Confirmation required")
    # In DRY_RUN/PAPER, we log and simulate close_all()
    evt = {
        "evt": "KILL_ALL",
        "payload": {"mode": settings.EXECUTOR_MODE.value, "simulated": settings.EXECUTOR_MODE != ExecutorMode.LIVE},
    }
    append_event(evt)
    # TODO: wire adapters.close_all() when adapters are implemented
    return JSONResponse({"status": "ok", "message": "Kill issued", "simulated": settings.EXECUTOR_MODE != ExecutorMode.LIVE})
