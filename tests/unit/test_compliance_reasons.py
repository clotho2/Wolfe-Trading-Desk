# tests/unit/test_compliance_reasons.py

from engine.ComplianceGuard.core import ComplianceGuard, Severity
from config.settings import Settings

class _AppendSpy(list):
    def __call__(self, obj):
        self.append(obj)

def _mk():
    spy = _AppendSpy()
    guard = ComplianceGuard(Settings(), append=spy)
    return guard, spy

def test_order_rate_emits_and_audits():
    g, spy = _mk()
    ev = g.check_order_rate(orders_last_60s=g.settings.ORDER_RATE_CAP_PER_60S + 1)
    assert ev and ev.code == "ORDER_RATE" and ev.severity == Severity.S1
    assert spy and spy[-1]["evt"] == "ORDER_RATE"

def test_news_blackout_freezes_entries():
    g, spy = _mk()
    ev = g.check_news_blackout(symbol="EURUSD", blackout=True)
    assert ev and ev.code == "NEWS_BLACKOUT" and ev.severity == Severity.S2
    assert spy[-1]["evt"] == "NEWS_BLACKOUT"

def test_atr_spike_triggers_freeze():
    g, spy = _mk()
    ev = g.check_atr_spike(symbol="XAUUSD", atr_ratio=2.1)
    assert ev and ev.code == "ATR_SPIKE" and ev.severity == Severity.S2
    assert spy[-1]["evt"] == "ATR_SPIKE"

def test_slippage_slo_breach_triggers_size_down_and_freeze():
    g, spy = _mk()
    ev = g.check_slippage_slo(symbol="GBPUSD", breaches_last_60m=3)
    assert ev and ev.code == "SLIPPAGE_SLO_BREACH" and ev.severity == Severity.S2
    assert spy[-1]["evt"] == "SLIPPAGE_SLO_BREACH"

def test_cluster_risk_cap_blocks_entries():
    g, spy = _mk()
    # open risk exceeds CLUSTER_CAP_MULT * single_trade_risk
    ev = g.check_cluster_risk(cluster_id="EUR", open_risk_pct=1.0, single_trade_risk_pct=0.7)
    assert ev and ev.code == "CLUSTER_RISK_CAP" and ev.severity == Severity.S2
    assert spy[-1]["evt"] == "CLUSTER_RISK_CAP"
