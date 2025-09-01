# path: shared/events/schema.py
from __future__ import annotations

ALLOWED_CODES = {
    "HA_LOCK_LOST",
    "RISK_ADAPT_APPLIED",
    "PARTIAL_FILL",
    "CORR_BLOCK",
    "GAP_HALT",
    "NUCLEAR_LOCKED",
    "NUCLEAR_RESUMED",
}


def is_allowed(code: str) -> bool:
    return code in ALLOWED_CODES

