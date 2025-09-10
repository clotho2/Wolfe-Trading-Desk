# path: adapters/base.py
from __future__ import annotations

import json
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

from config.settings import settings

SHADOW_DIR = Path("logs/shadow")
SHADOW_DIR.mkdir(parents=True, exist_ok=True)


@dataclass
class AdapterHealth:
    status: str
    detail: Optional[Dict[str, Any]] = None


@dataclass
class Order:
    symbol: str
    side: str
    qty: float


@dataclass
class ExecReport:
    status: str
    order: Optional[Order] = None
    order_id: Optional[str] = None
    changes: Optional[Dict[str, Any]] = None


class BrokerAdapter:
    def __init__(self) -> None:
        self._book: Dict[str, float] = {}

    # ---- public API ----
    async def place_order(self, order: Order) -> ExecReport:
        if str(getattr(settings.EXECUTOR_MODE, "value", settings.EXECUTOR_MODE)) == "SHADOW":
            self._shadow_log("place_order", order.__dict__)
            return ExecReport(status="SHADOW", order=order)
        if str(getattr(settings.EXECUTOR_MODE, "value", settings.EXECUTOR_MODE)) == "DRY_RUN":
            self._book[order.symbol] = self._book.get(order.symbol, 0.0) + (order.qty if order.side == "BUY" else -order.qty)
            return ExecReport(status="DRY_RUN", order=order)
        # LIVE path should be implemented by concrete adapters
        return await self._place_live(order)

    async def modify_order(self, order_id: str, **kwargs) -> ExecReport:
        if str(getattr(settings.EXECUTOR_MODE, "value", settings.EXECUTOR_MODE)) == "SHADOW":
            self._shadow_log("modify_order", {"order_id": order_id, **kwargs})
            return ExecReport(status="SHADOW", order_id=order_id, changes=kwargs)
        if str(getattr(settings.EXECUTOR_MODE, "value", settings.EXECUTOR_MODE)) == "DRY_RUN":
            return ExecReport(status="DRY_RUN", order_id=order_id, changes=kwargs)
        return await self._modify_live(order_id, **kwargs)

    async def close_all(self) -> None:
        if str(getattr(settings.EXECUTOR_MODE, "value", settings.EXECUTOR_MODE)) == "SHADOW":
            self._shadow_log("close_all", {})
            return None
        if str(getattr(settings.EXECUTOR_MODE, "value", settings.EXECUTOR_MODE)) == "DRY_RUN":
            self._book.clear()
            return None
        return await self._close_all_live()

    def health(self) -> AdapterHealth:
        return AdapterHealth(status="ok")

    # ---- to override for LIVE ----
    async def _place_live(self, order: Order) -> ExecReport:  # pragma: no cover - abstract
        raise NotImplementedError

    async def _modify_live(self, order_id: str, **kwargs) -> ExecReport:  # pragma: no cover - abstract
        raise NotImplementedError

    async def _close_all_live(self) -> None:  # pragma: no cover - abstract
        raise NotImplementedError

    # ---- helpers ----
    def _shadow_log(self, op: str, payload: Dict[str, Any]) -> None:
        stamp = datetime.now(timezone.utc).isoformat()
        entry = {"ts": stamp, "op": op, "payload": payload}
        (SHADOW_DIR / f"shadow-{datetime.now().date().isoformat()}.jsonl").open("a").write(json.dumps(entry) + "\n")
        
        # Also log to events for visualization
        self._log_trade_event(op, payload)
    
    def _log_trade_event(self, event_type: str, data: Dict[str, Any]) -> None:
        """Log trade events for dashboard visualization."""
        events_file = Path("logs/events.jsonl")
        events_file.parent.mkdir(parents=True, exist_ok=True)
        
        event = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "event": event_type,
            "data": data,
            "mode": str(getattr(settings.EXECUTOR_MODE, "value", settings.EXECUTOR_MODE))
        }
        
        try:
            with events_file.open("a") as f:
                f.write(json.dumps(event) + "\n")
        except Exception:
            pass  # Silently fail to not disrupt trading

