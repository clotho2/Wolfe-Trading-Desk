#!/usr/bin/env python3
"""Start the trading system with proper configuration and tick feed."""

import asyncio
import json
import logging
import os
import signal
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


class SimpleTick:
    """Simple tick data structure."""
    def __init__(self, symbol: str, bid: float, ask: float, timestamp: datetime):
        self.symbol = symbol
        self.bid = bid
        self.ask = ask
        self.timestamp = timestamp


class SimpleSMAStrategy:
    """Simplified SMA strategy without pydantic dependencies."""
    
    def __init__(self, symbol="EURUSD", size=0.01, fast_period=20, slow_period=50):
        self.symbol = symbol
        self.size = size
        self.fast_period = fast_period
        self.slow_period = slow_period
        self.prices = []
        self.fast_sma = None
        self.slow_sma = None
        self.prev_fast_sma = None
        self.prev_slow_sma = None
        self.last_signal = None
        self.position = 0.0
        self.enabled = True
        
        logger.info(f"SimpleSMAStrategy initialized: {symbol}, size={size}, fast={fast_period}, slow={slow_period}")
    
    def on_tick(self, tick: SimpleTick):
        """Process incoming tick data."""
        if not self.enabled or tick.symbol != self.symbol:
            return
        
        # Use mid price for SMA calculation
        mid_price = (tick.bid + tick.ask) / 2.0
        self.prices.append(mid_price)
        
        # Keep only last slow_period prices
        if len(self.prices) > self.slow_period:
            self.prices = self.prices[-self.slow_period:]
        
        # Need at least slow_period prices
        if len(self.prices) < self.slow_period:
            return
        
        # Store previous values
        self.prev_fast_sma = self.fast_sma
        self.prev_slow_sma = self.slow_sma
        
        # Calculate SMAs
        self.fast_sma = sum(self.prices[-self.fast_period:]) / self.fast_period
        self.slow_sma = sum(self.prices[-self.slow_period:]) / self.slow_period
        
        # Check for crossover signals
        self._check_signals(tick)
    
    def _check_signals(self, tick: SimpleTick):
        """Check for SMA crossover signals."""
        if (self.prev_fast_sma is None or self.prev_slow_sma is None or
            self.fast_sma is None or self.slow_sma is None):
            return
        
        # Golden cross (fast crosses above slow)
        if (self.prev_fast_sma <= self.prev_slow_sma and 
            self.fast_sma > self.slow_sma):
            self._handle_signal("BUY", tick)
        
        # Death cross (fast crosses below slow)
        elif (self.prev_fast_sma >= self.prev_slow_sma and 
              self.fast_sma < self.slow_sma):
            self._handle_signal("SELL", tick)
    
    def _handle_signal(self, side: str, tick: SimpleTick):
        """Handle trading signal."""
        try:
            # Simulate order placement
            order_data = {
                "symbol": self.symbol,
                "side": side,
                "qty": self.size,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "fast_sma": self.fast_sma,
                "slow_sma": self.slow_sma,
                "price": (tick.bid + tick.ask) / 2.0
            }
            
            # Log the trade
            self._log_trade("order_placed", order_data)
            
            # Update position
            if side == "BUY":
                self.position += self.size
            else:
                self.position -= self.size
            
            # Emit strategy signal event
            self._emit_strategy_signal(side, order_data)
            
            self.last_signal = side
            logger.info(f"Signal generated: {side} {self.size} {self.symbol} at {order_data['price']:.5f}")
            logger.info(f"Position: {self.position}, Fast SMA: {self.fast_sma:.5f}, Slow SMA: {self.slow_sma:.5f}")
            
        except Exception as e:
            logger.error(f"Error handling {side} signal: {e}", exc_info=True)
    
    def _log_trade(self, event_type: str, data: dict):
        """Log trade events."""
        events_file = Path("logs/events.jsonl")
        events_file.parent.mkdir(parents=True, exist_ok=True)
        
        event = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "event": event_type,
            "data": data,
            "mode": "DRY_RUN"
        }
        
        try:
            with events_file.open("a") as f:
                f.write(json.dumps(event) + "\n")
        except Exception as e:
            logger.error(f"Failed to log trade event: {e}")
    
    def _emit_strategy_signal(self, side: str, order_data: dict):
        """Emit strategy signal event."""
        events_file = Path("logs/events.jsonl")
        events_file.parent.mkdir(parents=True, exist_ok=True)
        
        event = {
            "ts": datetime.now().timestamp(),
            "reason": "STRATEGY_SIGNAL",
            "payload": {
                "strategy": "pilot_sma",
                "side": side,
                "symbol": self.symbol,
                "size": self.size,
                "fast_sma": self.fast_sma,
                "slow_sma": self.slow_sma,
                "result": "DRY_RUN"
            }
        }
        
        try:
            with events_file.open("a") as f:
                f.write(json.dumps(event) + "\n")
        except Exception as e:
            logger.error(f"Failed to emit strategy signal: {e}")
    
    def get_status(self):
        """Get strategy status."""
        return {
            "strategy": "pilot_sma",
            "enabled": self.enabled,
            "symbol": self.symbol,
            "position": self.position,
            "fast_sma": self.fast_sma,
            "slow_sma": self.slow_sma,
            "last_signal": self.last_signal,
            "price_buffer_size": len(self.prices)
        }


class TickGenerator:
    """Generates realistic market ticks."""
    
    def __init__(self, symbol="EURUSD", base_price=1.1000):
        self.symbol = symbol
        self.base_price = base_price
        self.current_price = base_price
        self.running = False
        
    def generate_tick(self) -> SimpleTick:
        """Generate a realistic tick."""
        # Simulate price movement with volatility
        change = (hash(str(time.time())) % 11 - 5) * 0.0001  # ±5 pips
        self.current_price += change
        
        # Keep price in reasonable range
        self.current_price = max(1.0500, min(1.1500, self.current_price))
        
        # Create bid/ask spread
        spread = 0.0002  # 2 pips
        bid = self.current_price - spread / 2
        ask = self.current_price + spread / 2
        
        return SimpleTick(
            symbol=self.symbol,
            bid=round(bid, 5),
            ask=round(ask, 5),
            timestamp=datetime.now(timezone.utc)
        )
    
    async def start(self, strategy: SimpleSMAStrategy, interval: float = 2.0):
        """Start generating ticks."""
        self.running = True
        logger.info(f"Starting tick generator for {self.symbol} (interval: {interval}s)")
        
        tick_count = 0
        while self.running:
            try:
                tick = self.generate_tick()
                strategy.on_tick(tick)
                tick_count += 1
                
                if tick_count % 10 == 0:
                    status = strategy.get_status()
                    logger.info(f"Tick {tick_count}: Price={tick.bid:.5f}/{tick.ask:.5f}, "
                              f"Fast SMA={status.get('fast_sma', 'N/A'):.5f if status.get('fast_sma') else 'N/A'}, "
                              f"Slow SMA={status.get('slow_sma', 'N/A'):.5f if status.get('slow_sma') else 'N/A'}, "
                              f"Position={status.get('position', 0)}")
                
                await asyncio.sleep(interval)
                
            except Exception as e:
                logger.error(f"Error generating tick: {e}", exc_info=True)
                await asyncio.sleep(interval)
    
    def stop(self):
        """Stop the tick generator."""
        self.running = False
        logger.info("Tick generator stopped")


class TradingSystem:
    """Main trading system coordinator."""
    
    def __init__(self):
        self.strategy = None
        self.tick_generator = None
        self.running = False
    
    async def start(self):
        """Start the trading system."""
        logger.info("Starting Trading System")
        logger.info("=" * 50)
        
        # Create strategy
        self.strategy = SimpleSMAStrategy(
            symbol="EURUSD",
            size=0.01,
            fast_period=20,
            slow_period=50
        )
        
        # Create tick generator
        self.tick_generator = TickGenerator("EURUSD", 1.1000)
        
        self.running = True
        
        # Start tick generation
        await self.tick_generator.start(self.strategy, interval=2.0)
    
    def stop(self):
        """Stop the trading system."""
        logger.info("Stopping Trading System")
        self.running = False
        if self.tick_generator:
            self.tick_generator.stop()
        
        if self.strategy:
            status = self.strategy.get_status()
            logger.info(f"Final Strategy Status: {status}")


async def main():
    """Main function."""
    # Set up signal handling
    system = TradingSystem()
    
    def signal_handler(signum, frame):
        logger.info(f"Received signal {signum}")
        system.stop()
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        await system.start()
    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt")
    finally:
        system.stop()


if __name__ == "__main__":
    asyncio.run(main())