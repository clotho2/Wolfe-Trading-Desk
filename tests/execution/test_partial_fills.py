# path: tests/execution/test_partial_fills.py
from __future__ import annotations

from engine.execution.partial_fills import OrderRequest, FillUpdate, evaluate_partial_fill


def test_partial_fill_continue_when_ok(monkeypatch):
    req = OrderRequest(order_id="A", symbol="EURUSD", side="BUY", qty=100, ts_ms=1000)
    upd = FillUpdate(order_id="A", filled_qty=80, spread_bps=10, ts_ms=1200)
    d = evaluate_partial_fill(req, upd, spread_cap_bps=20)
    assert d.action == "continue"


def test_partial_fill_retry_smaller(monkeypatch):
    req = OrderRequest(order_id="B", symbol="EURUSD", side="BUY", qty=100, ts_ms=1000)
    upd = FillUpdate(order_id="B", filled_qty=40, spread_bps=25, ts_ms=2000)
    d = evaluate_partial_fill(req, upd, spread_cap_bps=20)
    assert d.action == "retry_smaller"


def test_partial_fill_cancel_remainder(monkeypatch):
    req = OrderRequest(order_id="C", symbol="EURUSD", side="BUY", qty=100, ts_ms=1000)
    upd = FillUpdate(order_id="C", filled_qty=10, spread_bps=40, ts_ms=3000)
    d = evaluate_partial_fill(req, upd, spread_cap_bps=20)
    assert d.action == "cancel_remainder"
