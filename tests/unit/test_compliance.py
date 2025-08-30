from engine.ComplianceGuard.core import ComplianceGuard, Severity

def test_dd_soft_and_hard():
    g = ComplianceGuard()
    # Soft breach at 3.9% (default soft=3.8, hard=4.0)
    ev = g.evaluate(live_equity=96.1, snapshot_equity=100.0, floating_pl=0.0)
    codes = {e.code for e in ev}
    assert "DAILY_DD_SOFT" in codes

    # Hard breach at 4.0%
    g = ComplianceGuard()
    ev2 = g.evaluate(live_equity=96.0, snapshot_equity=100.0, floating_pl=0.0)
    codes2 = {e.code for e in ev2}
    assert "DAILY_DD_HARD" in codes2
    assert g.disabled is True
