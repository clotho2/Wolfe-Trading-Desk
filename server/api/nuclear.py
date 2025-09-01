# path: server/api/nuclear.py
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel

from config.settings import settings
from ops.audit.immutable_audit import append_event
from security.nuclear import prague_day_nonce, verify_signature
from shared.state.nuclear import clear as clear_nuclear, is_active, last_nonce_used, set_last_nonce
from shared.state.runtime import LockdownState, set_lockdown

router = APIRouter(prefix="/nuclear", tags=["nuclear"])


def require_token(authorization: Optional[str] = Header(None)):
    token = (authorization or "").removeprefix("Bearer ").strip()
    if token != settings.DASH_TOKEN:
        raise HTTPException(status_code=401, detail="Unauthorized")
    return True


class ResumePayload(BaseModel):
    signature_b64: str


@router.post("/re-enable", dependencies=[Depends(require_token)])
def re_enable(payload: ResumePayload):
    if not is_active():
        raise HTTPException(status_code=400, detail="Nuclear not active")

    nonce = prague_day_nonce()
    if last_nonce_used() == nonce:
        raise HTTPException(status_code=409, detail="Nonce already used (replay)")

    ok = verify_signature(payload.signature_b64, nonce.encode())
    if not ok:
        raise HTTPException(status_code=403, detail="Invalid signature")

    clear_nuclear()
    set_last_nonce(nonce)
    set_lockdown(LockdownState.NONE)
    append_event({"evt": "NUCLEAR_RESUMED", "payload": {"nonce": nonce}})
    return {"status": "ok"}
