# path: tests/acceptance/test_gap_guard.py
from engine.ComplianceGuard.core import ComplianceGuard
from config.settings import settings


def test_gap_below_threshold_no_halt(monkeypatch):
    monkeypatch.setattr(settings, "FEATURES_GAP_GUARD", True, raising=False)
    guard = ComplianceGuard(settings)
    res = guard.check_gap(open_price=114.9, prev_close=100.0)  # 14.9%
    assert res is None


def test_gap_at_threshold_halts(monkeypatch):
    monkeypatch.setattr(settings, "FEATURES_GAP_GUARD", True, raising=False)
    guard = ComplianceGuard(settings)
    res = guard.check_gap(open_price=115.0, prev_close=100.0)  # 15.0%
    assert res is not None and res.code == "GAP_HALT"


def test_gap_resume_path(monkeypatch):
    monkeypatch.setattr(settings, "FEATURES_GAP_GUARD", True, raising=False)
    guard = ComplianceGuard(settings)
    guard.check_gap(open_price=85.0, prev_close=100.0)  # trigger
    res = guard.gap_resume()
    assert res is not None and res.code == "GAP_RESUME"
