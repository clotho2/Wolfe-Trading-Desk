# path: engine/CopyDeCorr/core.py (legacy decor + correlation enforcement)
from __future__ import annotations

import itertools
import random
from dataclasses import dataclass, asdict
from typing import Any, Dict, List, Sequence, Tuple

import pandas as pd

from config.settings import settings
from ops.audit.immutable_audit import append_event


@dataclass
class DecorRecord:
    account_id: str
    strategy_fingerprint: str
    jitter_ms: int
    tilt: Dict[str, float]
    symbol_mask: List[str]


def apply_decorrelation(account_id: str, strategy_fingerprint: str, symbols: List[str]) -> DecorRecord:
    jitter_ms = random.randint(*settings.COPY_JITTER_MS)
    tilt_val = random.uniform(*settings.COPY_TILT_PCT)
    mask = symbols[:]  # placeholder rotation
    rec = DecorRecord(
        account_id=account_id,
        strategy_fingerprint=strategy_fingerprint,
        jitter_ms=jitter_ms,
        tilt={"ema_fast": round(tilt_val, 4)},
        symbol_mask=mask,
    )
    return rec


# --------------------------- v0.4.3 Correlation Cap ---------------------------
@dataclass
class CorrDecision:
    symbol_a: str
    symbol_b: str
    corr: float
    action: str  # "block" | "halve"


def _compute_window_corr(returns: pd.DataFrame, window: int) -> pd.DataFrame:
    if returns.shape[0] == 0:
        return pd.DataFrame()
    window = min(window, returns.shape[0])
    return returns.tail(window).corr()


def _usd_pair(symbol: str) -> bool:
    s = symbol.upper()
    return s.endswith("USD") or s.startswith("USD")


def enforce_correlation(
    open_symbols: Sequence[str],
    returns: pd.DataFrame,
    dxy_change_pct: float | None = None,
    *,
    window_days: int | None = None,
    threshold: float | None = None,
    action_default: str | None = None,
) -> List[CorrDecision]:
    """Return pairwise decisions meeting the threshold.

    Emits `CORR_BLOCK` events for traceability.
    """
    window = int(window_days or settings.CORR_WINDOW_DAYS)
    threshold = float(threshold or settings.CORR_BLOCK_THRESHOLD)
    action_default = (action_default or settings.CORR_THRESHOLD_ACTION).lower()

    if returns.empty or len(open_symbols) < 2:
        return []

    corr = _compute_window_corr(returns, window)
    decisions: List[CorrDecision] = []

    in_dxy_band = False
    if dxy_change_pct is not None:
        in_dxy_band = abs(float(dxy_change_pct)) <= float(settings.DXY_BAND_PCT)

    for a, b in itertools.combinations(open_symbols, 2):
        if a not in corr.columns or b not in corr.columns:
            continue
        rho = float(abs(corr.loc[a, b]))
        if rho >= threshold:
            action = action_default
            if in_dxy_band and _usd_pair(a) and _usd_pair(b):
                # In DXY band, we bias to configured action but remain consistent across the USD cluster
                action = action_default
            decisions.append(CorrDecision(a, b, rho, action))
            append_event({
                "evt": "CORR_BLOCK",
                "payload": {"symbol_a": a, "symbol_b": b, "rho": rho, "threshold": threshold, "action": action, "dxy_in_band": in_dxy_band},
            })

    return decisions


def group_compliance_enforcement(
    open_symbols: Sequence[str],
    returns: pd.DataFrame,
    dxy_change_pct: float | None = None,
) -> Tuple[List[str], Dict[str, float], List[CorrDecision]]:
    """Map pairwise decisions to ComplianceGuard effects.

    Returns (blocked_symbols, size_multipliers, raw_decisions)
    - If any USD pair crosses threshold *and* |ΔDXY| ≤ band → apply the chosen action to the entire USD cluster.
    - For non-USD pairs, apply action per symbol participation in any violating pair.
    - For action="block", symbol is added to blocked set.
    - For action="halve", symbol gets size multiplier 0.5.
    """
    decisions = enforce_correlation(open_symbols, returns, dxy_change_pct)
    blocked: set[str] = set()
    size_mul: Dict[str, float] = {}

    # Check DXY regime for USD cluster application
    in_dxy_band = False
    if dxy_change_pct is not None:
        in_dxy_band = abs(float(dxy_change_pct)) <= float(settings.DXY_BAND_PCT)

    usd_symbols = [s for s in open_symbols if _usd_pair(s)]
    any_usd_violation = any(_usd_pair(d.symbol_a) and _usd_pair(d.symbol_b) for d in decisions)

    if in_dxy_band and any_usd_violation:
        # Apply configured action consistently across USD cluster
        act = settings.CORR_THRESHOLD_ACTION
        if act == "block":
            blocked.update(usd_symbols)
        else:
            for s in usd_symbols:
                size_mul[s] = min(size_mul.get(s, 1.0), 0.5)

    # Apply per-pair actions for all pairs
    for d in decisions:
        for s in (d.symbol_a, d.symbol_b):
            if d.action == "block":
                blocked.add(s)
            else:
                size_mul[s] = min(size_mul.get(s, 1.0), 0.5)

    return sorted(blocked), size_mul, decisions
