# path: risk/adapters/risk_adapter.py
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Callable, Dict, Iterable, Optional

from config.settings import settings
from ops.audit.immutable_audit import append_event


class RiskMode(str, Enum):
    RATCHET = "ratchet"
    ADAPTIVE = "adaptive"
    BOTH = "both"


@dataclass
class RiskConfig:
    mode: RiskMode = RiskMode.RATCHET
    floor_pct: float = 0.25  # min multiplier vs proposed
    ceiling_pct: float = 1.50  # max multiplier vs proposed


class RiskAdapter:
    """Adaptive risk controller per Council v0.4.3.

    Modes:
      - ratchet: pass through ratchet sizing (no adaptive changes)
      - adaptive: scale proposed sizing by adaptive multiplier m in [floor, ceiling]
      - both: apply ratchet first, then adaptive; final = min(ratchet, adaptive)

    Emits reason code `RISK_ADAPT_APPLIED` only when adaptive *changes the outcome*.
    """

    def __init__(self, config: Optional[RiskConfig] = None, emit: Callable[[Dict], None] = append_event):
        self.config = config or RiskConfig(
            mode=RiskMode(settings.RISK_MODE),
            floor_pct=float(settings.RISK_FLOOR_PCT),
            ceiling_pct=float(settings.RISK_CEILING_PCT),
        )
        self.emit = emit
        # Clamp config sanity
        self.config.floor_pct = max(0.0, min(self.config.floor_pct, self.config.ceiling_pct))
        self.config.ceiling_pct = max(self.config.floor_pct, self.config.ceiling_pct)

    # ------------------------------- public API -------------------------------
    def adapt(
        self,
        proposed_size_pct: float,
        *,
        ratchet_size_pct: Optional[float] = None,
        recent_returns_pct: Optional[Iterable[float]] = None,
    ) -> float:
        mode = self.config.mode
        base = float(proposed_size_pct)
        ratch = float(ratchet_size_pct) if ratchet_size_pct is not None else base

        if mode == RiskMode.RATCHET:
            return ratch

        m = self._adaptive_multiplier(recent_returns_pct or [])
        adaptive_size = self._clamp(base * m)

        if mode == RiskMode.ADAPTIVE:
            final = adaptive_size
            self._maybe_emit(base, final, when="adaptive")
            return final

        # BOTH: take the smaller of ratchet vs adaptive
        final = min(ratch, adaptive_size)
        # Only emit if adaptive changed the outcome compared to ratchet
        if adaptive_size < ratch:
            self._maybe_emit(ratch, final, when="both")
        return final

    # ------------------------------ internals --------------------------------
    def _adaptive_multiplier(self, returns: Iterable[float]) -> float:
        """Compute a volatility-aware multiplier in [floor, ceiling].

        Deterministic mapping: lower realized volatility → higher multiplier (toward ceiling),
        higher volatility → lower multiplier (toward floor).

        Implementation:
          - vol = mean(abs(r)) over provided returns (fallback 0.01 if empty)
          - vol_ref = 0.02 (2%) as nominal FX daily band
          - score = min(1.0, max(0.0, vol / vol_ref))
          - m = ceiling - (ceiling - floor) * score
        """
        ret_list = list(returns)
        vol = sum(abs(x) for x in ret_list) / len(ret_list) if ret_list else 0.01
        vol_ref = 0.02
        score = max(0.0, min(1.0, vol / vol_ref))
        m = self.config.ceiling_pct - (self.config.ceiling_pct - self.config.floor_pct) * score
        return m

    def _clamp(self, value: float) -> float:
        lo, hi = self.config.floor_pct, self.config.ceiling_pct
        return max(lo * 0.999999, min(hi * 1.000001, value))  # lenient float guard

    def _maybe_emit(self, before: float, after: float, *, when: str) -> None:
        if abs(after - before) <= 1e-9:
            return
        self.emit(
            {
                "evt": "RISK_ADAPT_APPLIED",
                "payload": {
                    "mode": self.config.mode.value,
                    "before_pct": before,
                    "after_pct": after,
                    "floor_pct": self.config.floor_pct,
                    "ceiling_pct": self.config.ceiling_pct,
                    "context": when,
                },
            }
        )

