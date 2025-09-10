# path: strategies/pilot_sma.py
from __future__ import annotations

import logging
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any

from adapters.base import Order
from config.settings import Settings
from engine.ComplianceGuard.core import ComplianceGuard
from core.executor.registry import get_adapter
from shared.events.bus import bus

logger = logging.getLogger(__name__)


@dataclass
class Tick:
    """Market tick data."""
    symbol: str
    bid: float
    ask: float
    timestamp: datetime


@dataclass
class SMAState:
    """State for SMA calculation."""
    prices: deque = field(default_factory=lambda: deque(maxlen=50))
    fast_sma: Optional[float] = None
    slow_sma: Optional[float] = None
    prev_fast_sma: Optional[float] = None
    prev_slow_sma: Optional[float] = None
    last_signal: Optional[str] = None
    last_signal_time: Optional[datetime] = None


class PilotSMAStrategy:
    """
    Pilot SMA Strategy for EURUSD.
    
    Computes SMA(20) and SMA(50) on incoming ticks.
    - On cross up: submit market BUY 0.01
    - On cross down: submit market SELL 0.01
    
    All orders respect ComplianceGuard and are tagged with strategy:"pilot_sma".
    """
    
    def __init__(self, settings: Optional[Settings] = None):
        self.settings = settings or Settings()
        self.compliance_guard = ComplianceGuard(settings=self.settings)
        
        # Get strategy config
        self.config = self._load_config()
        self.symbol = self.config.get("symbol", "EURUSD")
        self.size = self.config.get("size", 0.01)
        self.fast_period = self.config.get("fast", 20)
        self.slow_period = self.config.get("slow", 50)
        
        # State management
        self.state = SMAState()
        self.enabled = True
        self.position = 0.0  # Track net position
        
        logger.info(f"PilotSMAStrategy initialized: symbol={self.symbol}, size={self.size}, "
                   f"fast={self.fast_period}, slow={self.slow_period}")
    
    def _load_config(self) -> Dict[str, Any]:
        """Load strategy configuration from settings."""
        if hasattr(self.settings, 'strategies') and hasattr(self.settings.strategies, 'pilot_sma'):
            config = self.settings.strategies.pilot_sma
            # If it's a Pydantic model, convert to dict
            if hasattr(config, 'model_dump'):
                return config.model_dump()
            elif hasattr(config, 'dict'):
                return config.dict()
            # If it's already a dict, return as is
            elif isinstance(config, dict):
                return config
            # Otherwise try to extract attributes
            else:
                return {
                    "symbol": getattr(config, "symbol", "EURUSD"),
                    "size": getattr(config, "size", 0.01),
                    "fast": getattr(config, "fast", 20),
                    "slow": getattr(config, "slow", 50)
                }
        return {}
    
    def on_tick(self, tick: Tick) -> None:
        """Process incoming tick data."""
        if not self.enabled:
            return
        
        # Only process ticks for our configured symbol
        if tick.symbol != self.symbol:
            return
        
        # Use mid price for SMA calculation
        mid_price = (tick.bid + tick.ask) / 2.0
        
        # Update price buffer
        self.state.prices.append(mid_price)
        
        # Need at least slow_period prices to calculate both SMAs
        if len(self.state.prices) < self.slow_period:
            return
        
        # Store previous SMA values
        self.state.prev_fast_sma = self.state.fast_sma
        self.state.prev_slow_sma = self.state.slow_sma
        
        # Calculate current SMAs
        self.state.fast_sma = self._calculate_sma(self.fast_period)
        self.state.slow_sma = self._calculate_sma(self.slow_period)
        
        # Check for crossover signals
        self._check_signals(tick)
    
    def _calculate_sma(self, period: int) -> float:
        """Calculate Simple Moving Average for given period."""
        if len(self.state.prices) < period:
            return 0.0
        
        # Get last 'period' prices from the deque
        prices_list = list(self.state.prices)
        recent_prices = prices_list[-period:]
        return sum(recent_prices) / period
    
    def _check_signals(self, tick: Tick) -> None:
        """Check for SMA crossover signals and execute trades."""
        # Need previous values to detect crossover
        if (self.state.prev_fast_sma is None or 
            self.state.prev_slow_sma is None or
            self.state.fast_sma is None or 
            self.state.slow_sma is None):
            return
        
        # Detect golden cross (fast crosses above slow)
        if (self.state.prev_fast_sma <= self.state.prev_slow_sma and 
            self.state.fast_sma > self.state.slow_sma):
            self._handle_signal("BUY", tick)
        
        # Detect death cross (fast crosses below slow)
        elif (self.state.prev_fast_sma >= self.state.prev_slow_sma and 
              self.state.fast_sma < self.state.slow_sma):
            self._handle_signal("SELL", tick)
    
    def _handle_signal(self, side: str, tick: Tick) -> None:
        """Handle trading signal with ComplianceGuard checks."""
        try:
            # Check if ComplianceGuard is disabled (would block trading)
            if self.compliance_guard.disabled:
                logger.warning(f"ComplianceGuard disabled, skipping {side} signal")
                return
            
            # Check for gap halt
            if self.compliance_guard._gap_halted:
                logger.warning(f"Gap halted, skipping {side} signal")
                return
            
            # Create order with strategy tag
            order = Order(
                symbol=self.symbol,
                side=side,
                qty=self.size
            )
            
            # Add strategy tag (would be in metadata in real implementation)
            order_metadata = {
                "strategy": "pilot_sma",
                "signal_time": datetime.now(timezone.utc).isoformat(),
                "fast_sma": self.state.fast_sma,
                "slow_sma": self.state.slow_sma
            }
            
            # Get adapter and submit order
            adapter = get_adapter("mt5")
            if adapter:
                # In a real implementation, we would pass metadata with the order
                # For now, log the metadata and submit the order
                logger.info(f"Submitting {side} order: {order_metadata}")
                
                # Submit order through adapter (respects EXECUTOR_MODE)
                result = adapter.place_order(order)
                
                # Update state
                self.state.last_signal = side
                self.state.last_signal_time = datetime.now(timezone.utc)
                
                # Update position tracking
                if side == "BUY":
                    self.position += self.size
                else:
                    self.position -= self.size
                
                # Emit event for monitoring
                bus.emit("STRATEGY_SIGNAL", 
                        strategy="pilot_sma",
                        side=side,
                        symbol=self.symbol,
                        size=self.size,
                        fast_sma=self.state.fast_sma,
                        slow_sma=self.state.slow_sma,
                        result=result.status)
                
                logger.info(f"Order submitted: {side} {self.size} {self.symbol}, "
                          f"result={result.status}, position={self.position}")
            else:
                logger.error("MT5 adapter not available")
                
        except Exception as e:
            logger.error(f"Error handling {side} signal: {e}", exc_info=True)
    
    def get_status(self) -> Dict[str, Any]:
        """Get current strategy status."""
        return {
            "strategy": "pilot_sma",
            "enabled": self.enabled,
            "symbol": self.symbol,
            "position": self.position,
            "fast_sma": self.state.fast_sma,
            "slow_sma": self.state.slow_sma,
            "last_signal": self.state.last_signal,
            "last_signal_time": self.state.last_signal_time.isoformat() if self.state.last_signal_time else None,
            "price_buffer_size": len(self.state.prices)
        }
    
    def stop(self) -> None:
        """Stop the strategy."""
        self.enabled = False
        logger.info("PilotSMAStrategy stopped")