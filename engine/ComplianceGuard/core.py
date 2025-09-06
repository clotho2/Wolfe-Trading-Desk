# path: engine/ComplianceGuard/core.py
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
from decimal import Decimal

import pandas as pd

from config.settings import Settings
from engine.CopyDeCorr.core import group_compliance_enforcement
from ops.audit.immutable_audit import append_event
from shared.events.bus import bus


class Severity(str, Enum):
    S1 = "S1"
    S2 = "S2"
    S3 = "S3"


@dataclass
class GuardResult:
    code: str
    severity: Severity
    detail: Dict[str, Any]


class ComplianceGuard:
    def __init__(self, settings: Optional[Settings] = None, append=append_event):
        self.settings = settings or Settings()
        self.append = append
        self.disabled: bool = False
        self.snapshot_equity: Decimal = Decimal("100")
        self._gap_halted: bool = False

    def _emit(self, code: str, severity: Severity, detail: Dict[str, Any], live_equity: Optional[float] = None) -> GuardResult:
        payload = {
            "code": code,
            "severity": severity.value,
            "detail": detail,
            "snapshot_equity": float(self.snapshot_equity),
            "live_equity": float(live_equity) if live_equity is not None else None,
            "now_utc": datetime.now(timezone.utc).isoformat(),
        }
        self.append({"evt": code, "payload": payload})
        # event bus is observability only
        bus.emit(code, **payload)
        return GuardResult(code=code, severity=severity, detail=detail)

    def check_daily_dd(self, live_equity: Decimal) -> Optional[GuardResult]:
        if self.snapshot_equity <= 0:
            return None
        dd = (self.snapshot_equity - live_equity) / self.snapshot_equity
        if dd >= Decimal(str(self.settings.DAILY_HARD_DD_PCT)):
            self.disabled = True
            return self._emit("DAILY_DD_HARD", Severity.S3, {"dd": float(dd)}, live_equity=float(live_equity))
        if dd >= Decimal(str(self.settings.DAILY_SOFT_FREEZE_PCT)):
            return self._emit("DAILY_DD_SOFT", Severity.S2, {"dd": float(dd)}, live_equity=float(live_equity))
        return None

    def check_gap(self, open_price: float, prev_close: float) -> Optional[GuardResult]:
        if not self.settings.FEATURES_GAP_GUARD:
            return None
        if prev_close <= 0:
            return None
        gap = abs(open_price - prev_close) / prev_close
        threshold = float(self.settings.GAP_ALERT_PCT)
        if gap >= threshold and not self._gap_halted:
            self._gap_halted = True
            res = self._emit(
                "GAP_HALT",
                Severity.S2,
                {"open": float(open_price), "prev_close": float(prev_close), "gap_pct": float(gap), "threshold": threshold, "action": "halt_new_entries"},
            )
            bus.emit("GAP_HALT", pct=float(gap), threshold=threshold)
            return res
        return None

    def gap_resume(self) -> Optional[GuardResult]:
        if self._gap_halted:
            self._gap_halted = False
            return self._emit("GAP_RESUME", Severity.S1, {"action": "resume_entries"})
        return None

    def check_correlation(self, open_symbols: List[str], returns: pd.DataFrame, dxy_change_pct: float | None = None) -> List[GuardResult]:
        blocked, size_mul, _ = group_compliance_enforcement(open_symbols, returns, dxy_change_pct)
        results: List[GuardResult] = []
        if blocked:
            results.append(self._emit("CORR_BLOCK", Severity.S2, {"symbols": blocked, "action": "block", "window_days": int(self.settings.CORR_WINDOW_DAYS), "threshold": float(self.settings.CORR_BLOCK_THRESHOLD)}))
            bus.emit("CORR_BLOCK", symbols=blocked, action="block", threshold=float(self.settings.CORR_BLOCK_THRESHOLD), window_days=int(self.settings.CORR_WINDOW_DAYS))
        halved = [s for s, m in size_mul.items() if m <= 0.5 and s not in blocked]
        if halved:
            results.append(self._emit("CORR_BLOCK", Severity.S1, {"symbols": halved, "action": "halve", "size_multiplier": 0.5, "window_days": int(self.settings.CORR_WINDOW_DAYS), "threshold": float(self.settings.CORR_BLOCK_THRESHOLD)}))
            bus.emit("CORR_BLOCK", symbols=halved, action="halve", threshold=float(self.settings.CORR_BLOCK_THRESHOLD), window_days=int(self.settings.CORR_WINDOW_DAYS))
        return results

    def evaluate(self, live_equity: float, snapshot_equity: Optional[float] = None, floating_pl: float = 0.0) -> List[GuardResult]:
        if snapshot_equity is not None:
            self.snapshot_equity = Decimal(str(snapshot_equity))
        res = self.check_daily_dd(Decimal(str(live_equity)))
        return [res] if res else []
