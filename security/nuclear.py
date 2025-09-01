# path: security/nuclear.py
from __future__ import annotations

import base64
from datetime import datetime, timezone
from typing import Tuple

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
from cryptography.hazmat.primitives import serialization
from zoneinfo import ZoneInfo

from config.settings import settings


def prague_day_nonce(now: datetime | None = None) -> str:
    tz = ZoneInfo(settings.PRAGUE_TZ)
    t = (now or datetime.now(timezone.utc)).astimezone(tz)
    return t.strftime("%Y-%m-%d")


def _load_pubkey(pubkey_b64: str) -> Ed25519PublicKey:
    raw = base64.b64decode(pubkey_b64)
    return Ed25519PublicKey.from_public_bytes(raw)


def verify_signature(sig_b64: str, message: bytes) -> bool:
    pub_b64 = settings.NUCLEAR_PUBKEY.strip()
    if not pub_b64:
        return False
    try:
        pk = _load_pubkey(pub_b64)
        sig = base64.b64decode(sig_b64)
        pk.verify(sig, message)
        return True
    except Exception:
        return False
