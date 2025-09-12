# path: adapters/mt5/mt5_adapter.py (no-op safety note; unchanged logic for flat_all)
from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Dict, List, Optional, TypedDict

from config.settings import settings
from .base import AdapterHealth, BrokerAdapter, ExecReport, Order
from pathlib import Path
import json
from .bridge_client import MT5ZMQClient, BridgeConfig

logger = logging.getLogger(__name__)


@dataclass
class _Position:
    symbol: str
    ticket: int


class CloseResult(TypedDict):
    symbol: str
    ticket: int
    status: str
    reason: str


class MT5Adapter(BrokerAdapter):
    def __init__(self, _settings=None):
        self.settings = _settings or settings
        self.connected = False
        self.server = ""
        self.login = ""
        self.last_tick = None
        self.watchlist_symbols = set()
        self._bridge: Optional[MT5ZMQClient] = None
        self._initialize_connection()

    def place_order(self, order: Order) -> ExecReport:
        # Get current execution mode
        mode = self.settings.EXECUTOR_MODE.value if hasattr(self.settings.EXECUTOR_MODE, "value") else str(self.settings.EXECUTOR_MODE)
        
        # Log the order for visualization
        self._log_trade_event("order_placed", {
            "symbol": order.symbol,
            "side": order.side,
            "qty": order.qty,
            "timestamp": datetime.utcnow().isoformat(),
            "mode": mode
        })
        
        # Return status based on actual execution mode
        if mode == "LIVE":
            # Use bridge for real execution
            try:
                return self._place_live_sync(order)
            except Exception as e:
                logger.error(f"LIVE order failed: {e}")
                return ExecReport(status="REJECTED", order=order)
        elif mode == "DRY_RUN":
            return ExecReport(status="DRY_RUN", order=order)
        elif mode == "SHADOW":
            return ExecReport(status="SHADOW", order=order)
        else:
            return ExecReport(status="UNKNOWN", order=order)
    
    def _place_live_sync(self, order: Order) -> ExecReport:
        """Place live order synchronously."""
        if not self._bridge:
            raise RuntimeError("MT5 bridge not initialized")
        meta = {"ts": datetime.now(timezone.utc).isoformat()}
        resp = self._bridge.place_order(order.symbol, order.side, float(order.qty), meta)
        status = "FILLED" if resp.get("ok") else "REJECTED"
        order_id = str(resp.get("order_id")) if resp.get("order_id") is not None else None
        self._log_trade_event("live_order_placed", {
            "symbol": order.symbol,
            "side": order.side,
            "qty": order.qty,
            "timestamp": datetime.utcnow().isoformat(),
            "mode": "LIVE",
            "bridge_status": status,
            "order_id": order_id,
        })
        return ExecReport(status=status, order=order, order_id=order_id)

    def modify_order(self, order_id: str, **kwargs) -> ExecReport:
        return ExecReport(status="DRY_RUN", order_id=order_id, changes=kwargs)

    def close_all(self) -> None:
        return None

    def health(self) -> AdapterHealth:
        return AdapterHealth(status="ok")

    async def list_open_positions(self) -> List[_Position]:
        return []

    async def close_position(self, p: _Position) -> bool:
        return True

    async def flat_all(self, reason: str) -> List[CloseResult]:
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

        for p in positions:
            ok = await self.close_position(p)
            results.append({"symbol": p.symbol, "ticket": p.ticket, "status": "closed" if ok else "skip", "reason": reason})
        return results

    def _initialize_connection(self) -> None:
        """Initialize MT5 connection and log status."""
        try:
            # Get MT5 connection settings
            if hasattr(self.settings, 'broker') and hasattr(self.settings.broker, 'mt5'):
                self.server = self.settings.broker.mt5.server or ""
                self.login = str(self.settings.broker.mt5.login) if self.settings.broker.mt5.login else ""
            
            # Check if MT5 adapter is enabled
            adapter_enabled = False
            if hasattr(self.settings, 'adapters') and hasattr(self.settings.adapters, 'mt5'):
                adapter_enabled = self.settings.adapters.mt5.get('enabled', True)
            
            if adapter_enabled and self.server and self.login:
                mode = self.settings.EXECUTOR_MODE.value if hasattr(self.settings.EXECUTOR_MODE, "value") else str(self.settings.EXECUTOR_MODE)
                if mode in ["DRY_RUN", "SHADOW"]:
                    self.connected = True
                    self.last_tick = datetime.utcnow()
                    logger.info(f"MT5 Adapter connected (mode={mode}, server={self.server}, login={self.login})")
                else:
                    # LIVE: start ZeroMQ bridge client
                    bridge_cfg = {}
                    if hasattr(self.settings, 'adapters') and hasattr(self.settings.adapters, 'mt5'):
                        bridge_cfg = (self.settings.adapters.mt5 or {}).get('bridge', {})
                    host = bridge_cfg.get('host', '127.0.0.1')
                    pub_port = int(bridge_cfg.get('pub_port', 5556))
                    req_port = int(bridge_cfg.get('req_port', 5557))
                    token = bridge_cfg.get('token', 'change-me')
                    symbols = [s.upper() for s in (self.settings.watchlist or [])]
                    cfg = BridgeConfig(host=host, pub_port=pub_port, req_port=req_port, token=token, symbols=symbols)
                    self._bridge = MT5ZMQClient(cfg, on_tick=self._on_bridge_tick)
                    self._bridge.start()
                    self.connected = True
                    self.last_tick = None
                    logger.info(f"MT5 Adapter LIVE via bridge (server={self.server}, login={self.login}, bridge={host}:{pub_port}/{req_port})")
            else:
                logger.warning(f"MT5 Adapter not connected: adapter_enabled={adapter_enabled}, server={bool(self.server)}, login={bool(self.login)}")
            
            # Subscribe to watchlist symbols
            self._subscribe_watchlist()
            
        except Exception as e:
            logger.error(f"Failed to initialize MT5 connection: {e}")
            self.connected = False

    def _on_bridge_tick(self, symbol: str, bid: float, ask: float, ts: datetime) -> None:
        """Forward ticks from bridge to strategy pipeline."""
        try:
            self.last_tick = ts
            # Forward to executor loop
            try:
                from core.executor.loop import process_tick
                from strategies.pilot_sma import Tick
                process_tick(Tick(symbol=symbol, bid=bid, ask=ask, timestamp=ts))
            except Exception as e:
                logger.error(f"Failed to forward tick: {e}")
        except Exception:
            pass

    def _subscribe_watchlist(self) -> None:
        """Subscribe to watchlist symbols and log any missing ones."""
        if not hasattr(self.settings, 'watchlist'):
            logger.info("No watchlist configured")
            return
        
        watchlist = self.settings.watchlist or []
        if not watchlist:
            logger.info("Watchlist is empty")
            return
        
        # In a real implementation, we would check available symbols from MT5
        # For now, we'll simulate with a common set of symbols
        available_symbols = {
            "EURUSD", "GBPUSD", "USDJPY", "USDCHF", "AUDUSD", "USDCAD", "NZDUSD",
            "EURJPY", "GBPJPY", "EURGBP", "XAUUSD", "XAGUSD", "US30", "US100", 
            "US500", "DE30", "UK100", "JP225", "BTCUSD", "ETHUSD"
        }
        
        missing_symbols = []
        for symbol in watchlist:
            if symbol.upper() in available_symbols:
                self.watchlist_symbols.add(symbol)
                logger.debug(f"Subscribed to symbol: {symbol}")
            else:
                missing_symbols.append(symbol)
        
        if missing_symbols:
            suggestions = self._get_symbol_suggestions(missing_symbols, available_symbols)
            logger.warning(f"Missing symbols in watchlist: {missing_symbols}")
            if suggestions:
                logger.info(f"Did you mean: {suggestions}")
        
        logger.info(f"Watchlist subscription complete: {len(self.watchlist_symbols)} symbols subscribed")

    def _get_symbol_suggestions(self, missing: List[str], available: set) -> Dict[str, List[str]]:
        """Get suggestions for missing symbols based on similarity."""
        suggestions = {}
        for symbol in missing:
            symbol_upper = symbol.upper()
            # Find similar symbols
            similar = []
            for avail in available:
                if symbol_upper in avail or avail in symbol_upper:
                    similar.append(avail)
                elif len(symbol_upper) == len(avail) and sum(c1 == c2 for c1, c2 in zip(symbol_upper, avail)) >= len(symbol_upper) - 2:
                    similar.append(avail)
            if similar:
                suggestions[symbol] = similar[:3]  # Limit to 3 suggestions
        return suggestions

    def get_status(self) -> Dict:
        """Get current adapter status."""
        return {
            "connected": self.connected,
            "server": self.server,
            "login": self.login,
            "last_tick": self.last_tick.isoformat() if self.last_tick else None,
            "watchlist_count": len(self.watchlist_symbols),
            "mode": self.settings.EXECUTOR_MODE.value if hasattr(self.settings.EXECUTOR_MODE, "value") else str(self.settings.EXECUTOR_MODE)
        }
    
    def _log_trade_event(self, event_type: str, data: Dict) -> None:
        """Log trade events for dashboard visualization."""
        events_file = Path("logs/events.jsonl")
        events_file.parent.mkdir(parents=True, exist_ok=True)
        
        event = {
            "timestamp": datetime.utcnow().isoformat(),
            "event": event_type,
            "data": data,
            "mode": self.settings.EXECUTOR_MODE.value if hasattr(self.settings.EXECUTOR_MODE, "value") else str(self.settings.EXECUTOR_MODE)
        }
        
        try:
            with events_file.open("a") as f:
                f.write(json.dumps(event) + "\n")
        except Exception:
            pass  # Silently fail to not disrupt trading
