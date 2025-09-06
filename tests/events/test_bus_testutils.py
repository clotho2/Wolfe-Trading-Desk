# path: tests/events/test_bus_testutils.py
from __future__ import annotations

import pytest

from shared.events.bus import bus
from shared.events.bus_testutils import assert_reason_once, drain, find


def test_assert_reason_once_with_contains():
    bus.emit("RISK_ADAPT_APPLIED", base=1.0, final=0.7)
    ev = assert_reason_once("RISK_ADAPT_APPLIED", contains={"final": 0.7})
    assert ev.payload["base"] == 1.0


def test_assert_reason_once_predicate():
    bus.emit("PARTIAL_FILL", requested=100, filled=40, action="retry_smaller")
    ev = assert_reason_once("PARTIAL_FILL", where=lambda e: e.payload.get("filled") == 40)
    assert ev.payload["action"] == "retry_smaller"


def test_assert_reason_once_raises_when_missing():
    # Ensure bus empty
    drain()
    with pytest.raises(AssertionError):
        assert_reason_once("GAP_HALT")
