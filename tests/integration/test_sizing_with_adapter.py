# path: tests/integration/test_sizing_with_adapter.py
from __future__ import annotations

from config.settings import settings
from engine.risk import sizing_flow
from tests.utils.returns_loader import load_sample_returns


def test_adapter_off_no_change(monkeypatch):
    monkeypatch.setattr(settings, "FEATURES_RISK_ADAPTER", False, raising=False)
    out, reason = sizing_flow(1.0, ratchet_size_pct=0.7, recent_returns_pct=[0.01, -0.01])
    assert out == 0.7 and reason is None


def test_adaptive_constrains_emits_reason(monkeypatch):
    monkeypatch.setattr(settings, "FEATURES_RISK_ADAPTER", True, raising=False)
    monkeypatch.setattr(settings, "RISK_MODE", "adaptive", raising=False)
    returns = load_sample_returns()
    out, reason = sizing_flow(1.0, ratchet_size_pct=0.95, recent_returns_pct=returns)
    assert out != 1.0 and reason and reason.get("evt") == "RISK_ADAPT_APPLIED"


def test_both_takes_min(monkeypatch):
    monkeypatch.setattr(settings, "FEATURES_RISK_ADAPTER", True, raising=False)
    monkeypatch.setattr(settings, "RISK_MODE", "both", raising=False)
    returns = load_sample_returns()
    out, reason = sizing_flow(1.0, ratchet_size_pct=0.8, recent_returns_pct=returns)
    assert out <= 0.8


def test_floor_ceiling_bounds(monkeypatch):
    monkeypatch.setattr(settings, "FEATURES_RISK_ADAPTER", True, raising=False)
    monkeypatch.setattr(settings, "RISK_MODE", "adaptive", raising=False)
    returns = load_sample_returns()
    out, _ = sizing_flow(1.0, ratchet_size_pct=0.99, recent_returns_pct=returns)
    assert 0.25 <= out <= 1.50

