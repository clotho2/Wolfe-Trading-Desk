# path: tests/acceptance/test_correlation_controls.py
import numpy as np
import pandas as pd

from config.settings import settings
from engine.ComplianceGuard.core import ComplianceGuard


def _mk_returns(rows=40, seed=7):
    rng = np.random.default_rng(seed)
    base = rng.normal(0, 0.01, size=rows)
    eur = base + rng.normal(0, 0.002, size=rows)
    gbp = base + rng.normal(0, 0.002, size=rows)
    # Below-threshold USDJPY
    jpy = rng.normal(0, 0.01, size=rows)
    return pd.DataFrame({"EURUSD": eur, "GBPUSD": gbp, "USDJPY": jpy})


def test_corr_block_default():
    settings.CORR_WINDOW_DAYS = 20
    settings.CORR_BLOCK_THRESHOLD = 0.70
    settings.CORR_THRESHOLD_ACTION = "block"
    guard = ComplianceGuard(settings)
    rets = _mk_returns()
    out = guard.check_correlation(["EURUSD", "GBPUSD", "USDJPY"], rets, dxy_change_pct=0.001)
    assert any(r.code == "CORR_BLOCK" and r.detail.get("action") == "block" for r in out)


def test_corr_halve_action():
    settings.CORR_WINDOW_DAYS = 20
    settings.CORR_BLOCK_THRESHOLD = 0.70
    settings.CORR_THRESHOLD_ACTION = "halve"
    guard = ComplianceGuard(settings)
    rets = _mk_returns()
    out = guard.check_correlation(["EURUSD", "GBPUSD"], rets)
    # Expect halve action emitted and not a block for these symbols
    assert any(r.detail.get("action") == "halve" for r in out)


def test_corr_window_calc():
    settings.CORR_WINDOW_DAYS = 10  # smaller window
    settings.CORR_BLOCK_THRESHOLD = 0.80  # raise threshold so older corr doesn't matter
    settings.CORR_THRESHOLD_ACTION = "block"
    guard = ComplianceGuard(settings)
    # Make last 10 rows weakly correlated by disrupting the tail
    rets = _mk_returns(rows=30)
    rets.iloc[-10:, 0] = np.random.default_rng(1).normal(0, 0.03, size=10)  # EURUSD jitter
    out = guard.check_correlation(["EURUSD", "GBPUSD"], rets)
    # With weak tail corr and higher threshold, no block should fire
    assert not any(r.detail.get("action") == "block" for r in out)


def test_dxy_band_regime():
    guard = ComplianceGuard(settings)
    settings.CORR_WINDOW_DAYS = 20
    settings.CORR_BLOCK_THRESHOLD = 0.72
    settings.CORR_THRESHOLD_ACTION = "halve"
    settings.DXY_BAND_PCT = 0.002  # ±0.2%
    rets = _mk_returns()
    # Slightly below threshold pair correlation → normally no action
    settings.CORR_BLOCK_THRESHOLD = 0.90
    out_normal = guard.check_correlation(["EURUSD", "GBPUSD", "USDJPY"], rets, dxy_change_pct=0.01)
    assert not any(r.detail.get("action") in {"block", "halve"} for r in out_normal)
    # In-band regime: if any USD pair is above the *lower* threshold, apply cluster-wide action
    settings.CORR_BLOCK_THRESHOLD = 0.70
    out_band = guard.check_correlation(["EURUSD", "GBPUSD", "USDJPY"], rets, dxy_change_pct=0.001)
    # Expect halve across USD cluster
    assert any(r.detail.get("action") == "halve" for r in out_band)

