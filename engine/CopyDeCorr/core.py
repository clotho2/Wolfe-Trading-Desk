# engine/CopyDeCorr/core.py
from __future__ import annotations

import itertools
import json
import random
from dataclasses import dataclass, asdict
from typing import Any, Dict, List, Sequence

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


@dataclass
class CorrDecision:
    symbol_a: str
    symbol_b: str
    corr: float
    action: str  # "block" | "halve"


def apply_decorrelation(account_id: str, strategy_fingerprint: str, symbols: List[str]) -> DecorRecord:
    """Legacy copy decorrelation (jitter/tilt/mask) — retained for parity.
    This does **not** enforce correlation caps.
    """
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

def _compute_window_corr(returns: pd.DataFrame, window: int = 20) -> pd.DataFrame:
    """Compute last-`window` pairwise Pearson correlation.

    Expects a DataFrame of log/percentage returns with columns as symbols and
    rows as equally spaced time buckets.
    """
    if returns.shape[0] < window:
        window = returns.shape[0]
    if window == 0:
        return pd.DataFrame()
    return returns.tail(window).corr()


def _usd_pair(symbol: str) -> bool:
    return "USD" in symbol.upper()


def enforce_correlation(
    open_symbols: Sequence[str],
    returns: pd.DataFrame,
    dxy_change_pct: float | None = None,
) -> List[CorrDecision]:
    """Enforce correlation caps per Council v0.4.3.

    - Block (default) or halve size when |ρ| ≥ settings.CORR_BLOCK_THRESHOLD
      across **rolling 20D** window of returns.
    - If provided, apply DXY support/resistance band: for USD pairs and
      |ΔDXY| ≤ settings.DXY_BAND_BPS bps (±0.20% default), prefer *block*.

    Emits immutable audit events with reason code `CORR_BLOCK`.
    """
    action_default = settings.CORR_THRESHOLD_ACTION
    threshold = float(settings.CORR_BLOCK_THRESHOLD)

    if returns.empty or len(open_symbols) < 2:
        return []

    corr = _compute_window_corr(returns, window=20)
    decisions: List[CorrDecision] = []

    # Determine DXY band condition once
    in_dxy_band = False
    if dxy_change_pct is not None:
        in_dxy_band = abs(float(dxy_change_pct)) <= (settings.DXY_BAND_BPS / 10_000.0)

    for a, b in itertools.combinations(open_symbols, 2):
        if a not in corr.columns or b not in corr.columns:
            continue
        rho = float(abs(corr.loc[a, b]))
        if rho >= threshold:
            action = action_default
            # If both are USD pairs and DXY is in tight band, bias to block
            if in_dxy_band and _usd_pair(a) and _usd_pair(b):
                action = "block"
            decisions.append(CorrDecision(a, b, rho, action))
            append_event(
                {
                    "evt": "CORR_BLOCK",
                    "payload": {
                        "symbol_a": a,
                        "symbol_b": b,
                        "rho": rho,
                        "threshold": threshold,
                        "action": action,
                        "dxy_in_band": in_dxy_band,
                    },
                }
            )

    return decisions
