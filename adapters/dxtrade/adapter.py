# path: adapters/dxtrade/adapter.py (stub + parity replay)
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import List

from adapters.mt5.base import BrokerAdapter, AdapterHealth, ExecReport, Order


@dataclass
class _DXPosition:
    symbol: str
    ticket: int


class DXtradeAdapter(BrokerAdapter):
    def __init__(self, replay_path: str | None = None):
        self.replay_path = Path(replay_path) if replay_path else None
        self._replay: List[dict] = []
        if self.replay_path and self.replay_path.exists():
            self._replay = [json.loads(l) for l in self.replay_path.read_text().splitlines() if l.strip()]

    def place_order(self, order: Order) -> ExecReport:
        return ExecReport(status="DRY_RUN", order=order)

    def modify_order(self, order_id: str, **kwargs) -> ExecReport:
        return ExecReport(status="DRY_RUN", order_id=order_id, changes=kwargs)

    def close_all(self) -> None:
        return None

    def health(self) -> AdapterHealth:
        return AdapterHealth(status="ok")
