# path: tests/risk/test_risk_adapter.py
from __future__ import annotations

import types

from config.settings import settings
from risk.adapters.risk_adapter import RiskAdapter, RiskConfig, RiskMode
from tests.utils.returns_loader import load_sample_returns


def _capture_emits():
    events = []
    def emit(evt):
        events.append(evt)
    return events, emit


def test_floor_ceiling_respected():
    returns = load_sample_returns()
    events, emit = _capture_emits()
    cfg = RiskConfig(mode=RiskMode.ADAPTIVE, floor_pct=0.25, ceiling_pct=1.5)
    ra = RiskAdapter(cfg, emit=emit)

    # Choose proposed such that unclamped multiplier would exceed ceiling for this dataset
    proposed = 1.0
    out = ra.adapt(proposed, recent_returns_pct=returns)
    assert 0.25 <= out <= 1.5

    # Force ceiling clamp by setting ceiling low
    cfg2 = RiskConfig(mode=RiskMode.ADAPTIVE, floor_pct=0.25, ceiling_pct=0.8)
    ra2 = RiskAdapter(cfg2, emit=emit)
    out2 = ra2.adapt(1.0, recent_returns_pct=returns)
    assert out2 <= 0.800001

    # Force floor clamp by setting floor high
    cfg3 = RiskConfig(mode=RiskMode.ADAPTIVE, floor_pct=0.9, ceiling_pct=1.5)
    ra3 = RiskAdapter(cfg3, emit=emit)
    out3 = ra3.adapt(1.0, recent_returns_pct=returns)
    assert out3 >= 0.899999


def test_mode_transitions_and_min_rule():
    returns = load_sample_returns()
    events, emit = _capture_emits()
    base = 1.0

    # ratchet → pass-through
    ra_r = RiskAdapter(RiskConfig(mode=RiskMode.RATCHET), emit=emit)
    ratch_only = ra_r.adapt(base, ratchet_size_pct=0.7, recent_returns_pct=returns)
    assert ratch_only == 0.7

    # adaptive → scaled
    ra_a = RiskAdapter(RiskConfig(mode=RiskMode.ADAPTIVE), emit=emit)
    a = ra_a.adapt(base, ratchet_size_pct=0.7, recent_returns_pct=returns)
    assert a != base  # scaled by multiplier

    # both → min(ratchet, adaptive)
    ra_b = RiskAdapter(RiskConfig(mode=RiskMode.BOTH), emit=emit)
    b = ra_b.adapt(base, ratchet_size_pct=0.7, recent_returns_pct=returns)
    assert b <= min(0.7, a)


def test_reason_codes_emitted_only_when_adaptive_changes_outcome():
    returns = load_sample_returns()
    events, emit = _capture_emits()

    # If ratchet already stricter, adaptive shouldn't emit
    ra_b = RiskAdapter(RiskConfig(mode=RiskMode.BOTH, floor_pct=0.25, ceiling_pct=1.5), emit=emit)
    out = ra_b.adapt(1.0, ratchet_size_pct=0.5, recent_returns_pct=returns)
    assert not any(e.get("evt") == "RISK_ADAPT_APPLIED" for e in events)

    # If adaptive constrains below ratchet, it should emit exactly once
    events.clear()
    ra_b2 = RiskAdapter(RiskConfig(mode=RiskMode.BOTH, floor_pct=0.25, ceiling_pct=0.6), emit=emit)
    out2 = ra_b2.adapt(1.0, ratchet_size_pct=0.9, recent_returns_pct=returns)
    assert any(e.get("evt") == "RISK_ADAPT_APPLIED" for e in events)
