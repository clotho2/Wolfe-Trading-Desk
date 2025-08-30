# engine/ComplianceGuard/core.py

from __future__ import annotations
from dataclasses import dataclass
from enum import Enum
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
from decimal import Decimal

from config.settings import Settings
from ops.audit.immutable_audit import append_event


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
    """
    Spec-true guard with explicit check_* methods and a backwards-compatible evaluate().
    All emissions are mirrored to the immutable audit via append_event(...).
    """

    def __init__(self, settings: Optional[Settings] = None, append=append_event):
        # Allow old tests to call ComplianceGuard() with no args
        self.settings = settings or Settings()
        self.append = append
        self.disabled: bool = False

        # State used by daily DD and optional counters
        self.snapshot_equity: Decimal = Decimal("100")  # updated by evaluate(..) if provided

    # ----------------- utilities -----------------

    def _emit(self, code: str, severity: Severity, detail: Dict[str, Any],
              live_equity: Optional[float] = None) -> GuardResult:
        payload = {
            "code": code,
            "severity": severity.value,
            "detail": detail,
            "snapshot_equity": float(self.snapshot_equity),
            "live_equity": float(live_equity) if live_equity is not None else None,
            "now_utc": datetime.now(timezone.utc).isoformat(),
        }
        # Mirror to immutable audit
        self.append({"evt": code, "payload": payload})
        return GuardResult(code=code, severity=severity, detail=detail)

    # ----------------- checks required by spec -----------------

    def check_daily_dd(self, live_equity: Decimal) -> Optional[GuardResult]:
        """3.8% soft freeze, ≤4.0% hard kill."""
        if self.snapshot_equity <= 0:
            return None
        dd = (self.snapshot_equity - live_equity) / self.snapshot_equity

        if dd >= Decimal(str(self.settings.DAILY_HARD_DD_PCT)):
            # Hard stop → disable executor
            self.disabled = True
            return self._emit(
                "DAILY_DD_HARD",
                Severity.S3,
                {"dd": float(dd)},
                live_equity=float(live_equity),
            )

        if dd >= Decimal(str(self.settings.DAILY_SOFT_FREEZE_PCT)):
            return self._emit(
                "DAILY_DD_SOFT",
                Severity.S2,
                {"dd": float(dd)},
                live_equity=float(live_equity),
            )
        return None

    def check_order_rate(self, orders_last_60s: int) -> Optional[GuardResult]:
        cap = int(self.settings.ORDER_RATE_CAP_PER_60S)
        if orders_last_60s > cap:
            return self._emit(
                "ORDER_RATE",
                Severity.S1,
                {"orders_last_60s": orders_last_60s, "cap": cap, "backoff_seconds": 60},
            )
        return None

    def check_news_blackout(self, symbol: str, blackout: bool) -> Optional[GuardResult]:
        # The calendar logic lives elsewhere; pass True here if blackout is active for symbol
        if blackout:
            return self._emit(
                "NEWS_BLACKOUT",
                Severity.S2,
                {"symbol": symbol, "action": "freeze_new_entries"},
            )
        return None

    def check_atr_spike(self, symbol: str, atr_ratio: float,
                        threshold: float = 2.0) -> Optional[GuardResult]:
        if atr_ratio > threshold:
            return self._emit(
                "ATR_SPIKE",
                Severity.S2,
                {"symbol": symbol, "atr_ratio": atr_ratio, "freeze_minutes": 60},
            )
        return None

    def check_slippage_slo(self, symbol: str, breaches_last_60m: int) -> Optional[GuardResult]:
        if breaches_last_60m >= 3:
            return self._emit(
                "SLIPPAGE_SLO_BREACH",
                Severity.S2,
                {"symbol": symbol, "breaches_last_60m": breaches_last_60m, "size_multiplier": 0.5, "freeze_minutes": 30},
            )
        return None

    def check_cluster_risk(self, cluster_id: str,
                           open_risk_pct: float,
                           single_trade_risk_pct: float) -> Optional[GuardResult]:
        cap = float(self.settings.CLUSTER_CAP_MULT) * float(single_trade_risk_pct)
        if float(open_risk_pct) > cap:
            return self._emit(
                "CLUSTER_RISK_CAP",
                Severity.S2,
                {"cluster_id": cluster_id, "open_risk_pct": open_risk_pct, "cap_pct": cap,
                 "action": "block_new_entries"},
            )
        return None

    # ----------------- legacy test compatibility -----------------

    def evaluate(self, live_equity: float, snapshot_equity: Optional[float] = None,
                 floating_pl: float = 0.0) -> List[GuardResult]:
        """
        Legacy shim used by tests/unit/test_compliance.py.
        If snapshot_equity is provided, update it; then run the daily DD check only.
        """
        if snapshot_equity is not None:
            self.snapshot_equity = Decimal(str(snapshot_equity))
        res = self.check_daily_dd(Decimal(str(live_equity)))
        return [res] if res else []
