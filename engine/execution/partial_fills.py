# path: engine/execution/partial_fills.py
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Optional

from config.settings import settings
from ops.audit.immutable_audit import append_event


@dataclass
class OrderRequest:
    order_id: str
    symbol: str
    side: str  # BUY/SELL
    qty: float
    ts_ms: int


@dataclass
class FillUpdate:
    order_id: str
    filled_qty: float
    spread_bps: float
    ts_ms: int


@dataclass
class PartialFillDecision:
    action: str  # cancel_remainder | retry_smaller | continue
    reason: str


SPREAD_CAP_BPS_DEFAULT = 20.0


def evaluate_partial_fill(
    req: OrderRequest,
    upd: FillUpdate,
    *,
    spread_cap_bps: Optional[float] = None,
) -> PartialFillDecision:
    """Policy per spec:
    - Always emit PARTIAL_FILL with {requested, filled, elapsed_ms, action}.
    - If fill_ratio < 60% and spread > cap → CANCEL_REMAINDER or RETRY smaller.
      We choose CANCEL_REMAINDER if spread > 1.5*cap, else RETRY smaller.
    - Otherwise CONTINUE.
    """
    cap = float(spread_cap_bps if spread_cap_bps is not None else getattr(settings, "SPREAD_CAP_BPS", SPREAD_CAP_BPS_DEFAULT))
    filled = max(0.0, float(upd.filled_qty))
    requested = max(1e-9, float(req.qty))
    ratio = filled / requested

    action = "continue"
    reason = "ok"

    if ratio < 0.60 and upd.spread_bps > cap:
        action = "cancel_remainder" if upd.spread_bps > 1.5 * cap else "retry_smaller"
        reason = "low_fill_high_spread"

    payload: Dict[str, object] = {
        "order_id": req.order_id,
        "symbol": req.symbol,
        "requested": requested,
        "filled": filled,
        "elapsed_ms": max(0, int(upd.ts_ms - req.ts_ms)),
        "action": action,
        "fill_ratio": round(ratio, 4),
        "spread_bps": round(float(upd.spread_bps), 3),
    }
    append_event({"evt": "PARTIAL_FILL", "payload": payload})
    return PartialFillDecision(action=action, reason=reason)
