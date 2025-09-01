# path: tests/unit/test_correlation.py
import numpy as np
import pandas as pd

from config.settings import settings
from engine.CopyDeCorr.core import enforce_correlation


def _mk_returns(rows=40):
    rng = np.random.default_rng(42)
    base = rng.normal(0, 0.01, size=rows)
    # Highly correlated series for EURUSD/GBPUSD
    eur = base + rng.normal(0, 0.002, size=rows)
    gbp = base + rng.normal(0, 0.002, size=rows)
    # Less correlated USDJPY
    jpy = rng.normal(0, 0.01, size=rows)
    return pd.DataFrame({"EURUSD": eur, "GBPUSD": gbp, "USDJPY": jpy})


def test_corr_block_default():
    settings.CORR_BLOCK_THRESHOLD = 0.70
    settings.CORR_THRESHOLD_ACTION = "block"
    rets = _mk_returns()
    dec = enforce_correlation(["EURUSD", "GBPUSD", "USDJPY"], rets)
    assert any(d.action == "block" and {d.symbol_a, d.symbol_b} == {"EURUSD", "GBPUSD"} for d in dec)


def test_corr_halve_action():
    settings.CORR_BLOCK_THRESHOLD = 0.70
    settings.CORR_THRESHOLD_ACTION = "halve"
    rets = _mk_returns()
    dec = enforce_correlation(["EURUSD", "GBPUSD"], rets)
    assert any(d.action == "halve" for d in dec)


def test_corr_dxy_band_bias_to_block():
    settings.CORR_BLOCK_THRESHOLD = 0.70
    settings.CORR_THRESHOLD_ACTION = "halve"  # default would halve
    settings.DXY_BAND_BPS = 20  # ±0.20%
    rets = _mk_returns()
    # in-band DXY change should flip to block for USD pairs
    dec = enforce_correlation(["EURUSD", "GBPUSD"], rets, dxy_change_pct=0.001)
    assert any(d.action == "block" for d in dec)
