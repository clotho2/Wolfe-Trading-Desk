# path: tests/profiles/test_ftmo.py
from __future__ import annotations

from datetime import datetime, timezone

from engine.profiles.ftmo import friday_cutoff_active, cap_per_trade_risk


def test_friday_cutoff_logic():
    # Friday 14:30 UTC with 14:00 cutoff
    dt = datetime(2025, 8, 29, 14, 30, tzinfo=timezone.utc)
    assert friday_cutoff_active(dt) is True
    # Thursday same time
    dt2 = datetime(2025, 8, 28, 14, 30, tzinfo=timezone.utc)
    assert friday_cutoff_active(dt2) is False


def test_phase2_cap():
    assert cap_per_trade_risk(1.2, phase2=True) == 0.5
    assert cap_per_trade_risk(0.3, phase2=True) == 0.3
