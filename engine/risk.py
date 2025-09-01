# path: engine/risk.py (integrate RiskAdapter feature-gated sizing flow)
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Optional, Tuple

from config.settings import settings
from ops.audit.immutable_audit import append_event
from risk.adapters.risk_adapter import RiskAdapter, RiskConfig


@dataclass
class RiskParams:
    atr: float
    account_equity: float
    single_trade_risk_pct: float


def atr_normalized_size(params: RiskParams) -> float:
    # Simple placeholder: equity * risk% / (ATR * scale)
    scale = max(params.atr, 1e-6)
    return (params.account_equity * params.single_trade_risk_pct) / scale


def cluster_cap(max_single_trade_risk: float) -> float:
    return max_single_trade_risk * settings.CLUSTER_CAP_MULT


def _vol_metric(recent_returns_pct: Iterable[float] | None) -> float:
    lst = list(recent_returns_pct or [])
    if not lst:
        return 0.01
    return sum(abs(x) for x in lst) / len(lst)


def sizing_flow(
    strategy_size_pct: float,
    *,
    ratchet_size_pct: Optional[float] = None,
    recent_returns_pct: Optional[Iterable[float]] = None,
) -> Tuple[float, Optional[dict]]:
    """Deterministic ordering sizing flow with optional RiskAdapter.

    Returns (final_size_pct, reason_payload_or_none)
    """
    base = float(strategy_size_pct)
    ratch = float(ratchet_size_pct) if ratchet_size_pct is not None else base
    reason = None

    if not settings.FEATURES_RISK_ADAPTER:
        return ratch, None

    # Silence internal RA emission; engine will emit one enriched event if constraining.
    ra = RiskAdapter(emit=lambda _evt: None)
    adaptive = ra.adapt(base, ratchet_size_pct=ratch, recent_returns_pct=recent_returns_pct)

    final = ratch
    if settings.RISK_MODE == "adaptive":
        final = adaptive
    elif settings.RISK_MODE == "both":
        final = min(ratch, adaptive)
    else:  # ratchet
        final = ratch

    # Emit reason only if adaptive actually constrained outcome
    if final < ratch or (settings.RISK_MODE == "adaptive" and final != base):
        vol = _vol_metric(recent_returns_pct)
        reason = {
            "evt": "RISK_ADAPT_APPLIED",
            "payload": {
                "mode": settings.RISK_MODE,
                "base": base,
                "ratchet": ratch,
                "adaptive": adaptive,
                "final": final,
                "floor_pct": settings.RISK_FLOOR_PCT,
                "ceiling_pct": settings.RISK_CEILING_PCT,
                "vol_metric": vol,
            },
        }
        append_event(reason)

    return final, reason
