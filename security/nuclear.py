# path: security/nuclear.py
from __future__ import annotations

import base64
from datetime import datetime, timezone
from typing import Optional

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

from config.settings import settings
from ops.audit.immutable_audit import append_event
from shared.events.bus import bus
from shared.state.nuclear import clear as clear_state, engage as set_state, is_active
from shared.state.runtime import LockdownState, set_lockdown


def day_nonce(now: Optional[datetime] = None, tz: str = "Europe/Prague") -> str:
    import zoneinfo

    dt = (now or datetime.now(timezone.utc)).astimezone(zoneinfo.ZoneInfo(tz))
    return dt.strftime("%Y%m%d")


def verify(signature_b64: str, message: bytes, pubkey_b64: str | None = None) -> bool:
    pub_b64 = (pubkey_b64 or settings.NUCLEAR_PUBKEY or "").strip()
    if not pub_b64:
        return False
    try:
        pk = Ed25519PublicKey.from_public_bytes(base64.b64decode(pub_b64))
        pk.verify(base64.b64decode(signature_b64), message)
        return True
    except Exception:
        return False


async def engage() -> None:
    if is_active():
        return
    set_state()
    set_lockdown(LockdownState.SPLIT_BRAIN)
    from core.executor.registry import get_adapter

    adapter = get_adapter("mt5") or get_adapter(None)
    if adapter is not None:
        await adapter.flat_all("nuclear")
    append_event({"evt": "NUCLEAR_LOCKED", "payload": {}})
    bus.emit("NUCLEAR_LOCKED")
