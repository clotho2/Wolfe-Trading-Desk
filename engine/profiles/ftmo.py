# path: engine/profiles/ftmo.py
from __future__ import annotations

from datetime import datetime, time, timezone
from typing import Optional

from zoneinfo import ZoneInfo

from config.settings import settings


def _parse_hhmm(s: str) -> time:
    hh, mm = s.strip().split(":")
    return time(int(hh), int(mm))


def friday_cutoff_active(now: Optional[datetime] = None) -> bool:
    """True if it's Friday and past the cutoff time in GMT."""
    dt = (now or datetime.now(timezone.utc)).astimezone(ZoneInfo("UTC"))
    if dt.weekday() != 4:
        return False
    cutoff = _parse_hhmm(settings.FTMO_FRIDAY_CUTOFF_GMT)
    return dt.time() >= cutoff


def cap_per_trade_risk(risk_pct: float, phase2: bool = True) -> float:
    """Apply FTMO Phase 2 per-trade risk cap if enabled."""
    cap = float(settings.FTMO_PHASE2_MAX_PER_TRADE_RISK_PCT) if phase2 else 100.0
    return min(float(risk_pct), cap)
