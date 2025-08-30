from dataclasses import dataclass
from enum import Enum
from typing import Optional, List, Dict
from config.settings import settings
from ops.audit.immutable_audit import append_event

class Severity(str, Enum):
    S1 = "S1"
    S2 = "S2"
    S3 = "S3"

@dataclass
class GuardEvent:
    code: str
    severity: Severity
    detail: Dict

class ComplianceGuard:
    def __init__(self):
        self.disabled = False

    def evaluate(self, live_equity: float, snapshot_equity: float, floating_pl: float) -> List[GuardEvent]:
        events: List[GuardEvent] = []
        # Daily drawdown check (soft/hard)
        dd = (snapshot_equity - live_equity) / max(snapshot_equity, 1e-9)
        if dd >= settings.DAILY_SOFT_FREEZE_PCT and dd < settings.DAILY_HARD_DD_PCT:
            events.append(GuardEvent("DAILY_DD_SOFT", Severity.S2, {"dd": dd}))
        if dd >= settings.DAILY_HARD_DD_PCT:
            events.append(GuardEvent("DAILY_DD_HARD", Severity.S3, {"dd": dd}))
            self.disabled = True
        # Mirror to audit
        for e in events:
            append_event({"evt": e.code, "payload": {"severity": e.severity, **e.detail}})
        return events
