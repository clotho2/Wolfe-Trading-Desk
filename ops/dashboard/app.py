# path: ops/dashboard/app.py (call start_executor gated by ENV+feature)
from __future__ import annotations

from typing import Optional

from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel

from config.settings import ExecutorMode, Settings, settings
from core.executor.bootstrap import start_executor
from engine.timebox import now_prague, prague_reset_countdown
from ops.audit.immutable_audit import append_event
from ops.ha.bootstrap import start_ha, status as ha_status

app = FastAPI(title="WolfeDesk v0.4.3 Dashboard")


@app.on_event("startup")
async def _startup():
    await start_ha(app, Settings())
    if settings.FEATURES_AUTO_REGISTER_MT5 and settings.ENV in {"dev", "test"}:
        start_executor(Settings())


# ... (rest of file unchanged from prior canvas commit) ...


# ------------------------------- COMMIT 04 ----------------------------------
# path: shared/state/nuclear.py
from __future__ import annotations

from typing import Optional

_active: bool = False
_last_nonce_used: Optional[str] = None


def engage() -> None:
    global _active
    _active = True


def clear() -> None:
    global _active
    _active = False


def is_active() -> bool:
    return _active


def last_nonce_used() -> Optional[str]:
    return _last_nonce_used


def set_last_nonce(nonce: str) -> None:
    global _last_nonce_used
    _last_nonce_used = nonce
