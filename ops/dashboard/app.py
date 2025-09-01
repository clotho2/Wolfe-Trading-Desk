# ops/dashboard/app.py
from __future__ import annotations

from typing import Optional

from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.responses import JSONResponse

from config.settings import ExecutorMode, settings
from engine.timebox import now_prague, prague_reset_countdown
from ops.audit.immutable_audit import append_event

app = FastAPI(title="WolfeDesk v0.4.3 Dashboard")


# ------------------------------ Auth / Headers ------------------------------

def require_token(authorization: Optional[str] = Header(None)):
    token = (authorization or "").removeprefix("Bearer ").strip()
    if token != settings.DASH_TOKEN:
        raise HTTPException(status_code=401, detail="Unauthorized")
    return True


@app.middleware("http")
async def mode_header(request, call_next):  # type: ignore[no-untyped-def]
    response = await call_next(request)
    # Watermark all responses with current executor mode
    response.headers["X-Wolfe-Mode"] = settings.EXECUTOR_MODE.value
    return response


# --------------------------------- Routes ----------------------------------


class KillConfirm(BaseModel := __import__("pydantic").BaseModel):  # local type hint
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

    # In DRY_RUN/SHADOW, log-only (no side effects). LIVE wiring will close_all().
    evt = {
        "evt": "KILL_ALL",
        "payload": {
            "mode": settings.EXECUTOR_MODE.value,
            "simulated": settings.EXECUTOR_MODE != ExecutorMode.LIVE,
        },
    }
    append_event(evt)
    return JSONResponse(
        {
            "status": "ok",
            "message": "Kill issued",
            "simulated": settings.EXECUTOR_MODE != ExecutorMode.LIVE,
        }
    )
