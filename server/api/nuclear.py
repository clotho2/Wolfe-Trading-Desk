# path: server/api/nuclear.py
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel

from config.settings import settings
from ops.audit.immutable_audit import append_event
from security.nuclear import day_nonce, verify
from shared.events.bus import bus
from shared.state.nuclear import clear as clear_nuclear, is_active, last_nonce_used, set_last_nonce
from shared.state.runtime import LockdownState, set_lockdown

router = APIRouter(prefix="/nuclear", tags=["nuclear"])


def require_token(authorization: Optional[str] = Header(None)):
    token = (authorization or "").removeprefix("Bearer ").strip()
    if token != settings.DASH_TOKEN:
        raise HTTPException(status_code=401, detail="Unauthorized")
    return True


class SignaturePayload(BaseModel):
    signature_b64: str


@router.post("/engage", dependencies=[Depends(require_token)])
async def engage_route():
    from security.nuclear import engage as do_engage

    await do_engage()
    return {"status": "ok"}


@router.post("/reenable", dependencies=[Depends(require_token)])
def reenable_route(payload: SignaturePayload):
    if not is_active():
        raise HTTPException(status_code=400, detail="Nuclear not active")
    nonce = day_nonce()
    if last_nonce_used() == nonce:
        raise HTTPException(status_code=409, detail="Nonce already used")
    if not verify(payload.signature_b64, nonce.encode()):
        raise HTTPException(status_code=403, detail="Invalid signature")
    clear_nuclear()
    set_last_nonce(nonce)
    set_lockdown(LockdownState.NONE)
    append_event({"evt": "NUCLEAR_RESUMED", "payload": {"nonce": nonce}})
    bus.emit("NUCLEAR_RESUMED", nonce=nonce)
    return {"status": "ok"}
