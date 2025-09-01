# path: adapters/mt5/adapter.py (shim to existing class)
from __future__ import annotations

import os
from typing import List, TypedDict

from .mt5_adapter import MT5Adapter as _MT5


class CloseResult(TypedDict):
    symbol: str
    ticket: int
    status: str
    reason: str


class MT5Adapter(_MT5):
    def assert_live_allowed(self) -> None:
        # Guard against accidental live sessions in CI/dev
        if os.getenv("SAFETY_NO_LIVE") == "1":
            raise AssertionError("Live sessions disabled by SAFETY_NO_LIVE=1")
