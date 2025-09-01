# path: adapters/mt5/mt5_adapter.py
from __future__ import annotations

from dataclasses import dataclass
from typing import List, TypedDict

from config.settings import settings
from .base import AdapterHealth, BrokerAdapter, ExecReport, Order


@dataclass
class _Position:
    symbol: str
    ticket: int


class CloseResult(TypedDict):
    symbol: str
    ticket: int
    status: str  # "closed" | "skip" | "shadow"
    reason: str


class MT5Adapter(BrokerAdapter):
    def __init__(self, _settings=None):
        self.settings = _settings or settings

    # ---- existing sync placeholders ----
    def place_order(self, order: Order) -> ExecReport:
        return ExecReport(status="DRY_RUN", order=order)

    def modify_order(self, order_id: str, **kwargs) -> ExecReport:
        return ExecReport(status="DRY_RUN", order_id=order_id, changes=kwargs)

    def close_all(self) -> None:  # legacy sync API, kept for compatibility
        return None

    def health(self) -> AdapterHealth:
        return AdapterHealth(status="ok")

    # ---- new async HA/Nuclear drill hook ----
    async def list_open_positions(self) -> List[_Position]:  # stub for drills
        return []

    async def close_position(self, p: _Position) -> bool:  # stub for drills
        return True

    async def flat_all(self, reason: str) -> List[CloseResult]:
        """Close all positions. SHADOW-safe (no broker calls)."""
        mode = self.settings.EXECUTOR_MODE.value if hasattr(self.settings.EXECUTOR_MODE, "value") else str(self.settings.EXECUTOR_MODE)
        positions = await self.list_open_positions()
        results: List[CloseResult] = []

        if mode == "SHADOW":
            for p in positions:
                results.append({"symbol": p.symbol, "ticket": p.ticket, "status": "shadow", "reason": reason})
            return results

        if mode == "DRY_RUN":
            for p in positions:
                results.append({"symbol": p.symbol, "ticket": p.ticket, "status": "skip", "reason": "dry_run"})
            return results

        # LIVE path
        for p in positions:
            ok = await self.close_position(p)
            results.append({"symbol": p.symbol, "ticket": p.ticket, "status": "closed" if ok else "skip", "reason": reason})
        return results
