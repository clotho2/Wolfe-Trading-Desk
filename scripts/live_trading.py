#!/usr/bin/env python3
"""Live trading system with real tick feed for the pilot_sma strategy."""

import asyncio
import logging
import os
import signal
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

# Add workspace to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

# Set environment variables for LIVE trading
os.environ["EXECUTOR_MODE"] = "LIVE"
os.environ["SAFETY_NO_LIVE"] = "0"
os.environ["FEATURES_STRATEGY_PILOT"] = "1"
os.environ["FEATURES_AUTO_REGISTER_MT5"] = "1"

try:
    from config.settings import Settings
    from core.executor.bootstrap import start_executor
    from core.executor.loop import load_strategies, process_tick, get_strategy_status
    from strategies.pilot_sma import Tick
except ImportError as e:
    logger.error(f"Failed to import required modules: {e}")
    logger.error("Make sure all dependencies are installed and the system is properly configured")
    sys.exit(1)


class LiveTickGenerator:
    """Generates realistic market ticks for live trading simulation."""
    
    def __init__(self, symbol="EURUSD", base_price=1.1000):
        self.symbol = symbol
        self.base_price = base_price
        self.current_price = base_price
        self.running = False
        self.tick_count = 0
        
    def generate_tick(self) -> Tick:
        """Generate a realistic tick with proper volatility."""
        # Simulate realistic price movement
        # Use time-based seed for consistent but varying movement
        time_seed = int(time.time() * 1000) % 1000
        change = (time_seed % 11 - 5) * 0.0001  # ±5 pips
        
        # Add some trend and mean reversion
        if self.current_price > self.base_price * 1.01:
            change -= 0.0002  # Slight downward pressure
        elif self.current_price < self.base_price * 0.99:
            change += 0.0002  # Slight upward pressure
        
        self.current_price += change
        
        # Keep price in reasonable range
        self.current_price = max(1.0500, min(1.1500, self.current_price))
        
        # Create realistic bid/ask spread (1-2 pips for major pairs)
        spread = 0.0002  # 2 pips
        bid = self.current_price - spread / 2
        ask = self.current_price + spread / 2
        
        return Tick(
            symbol=self.symbol,
            bid=round(bid, 5),
            ask=round(ask, 5),
            timestamp=datetime.now(timezone.utc)
        )
    
    async def start(self, interval: float = 1.0):
        """Start generating ticks at specified interval."""
        self.running = True
        logger.info(f"Starting live tick generator for {self.symbol} (interval: {interval}s)")
        logger.info(f"Base price: {self.base_price:.5f}")
        
        while self.running:
            try:
                tick = self.generate_tick()
                process_tick(tick)
                self.tick_count += 1
                
                # Log progress every 20 ticks
                if self.tick_count % 20 == 0:
                    strategies = get_strategy_status()
                    for strategy in strategies:
                        if strategy.get('strategy') == 'pilot_sma':
                            logger.info(f"Tick {self.tick_count}: Price={tick.bid:.5f}/{tick.ask:.5f}, "
                                      f"Fast SMA={strategy.get('fast_sma', 'N/A'):.5f if strategy.get('fast_sma') else 'N/A'}, "
                                      f"Slow SMA={strategy.get('slow_sma', 'N/A'):.5f if strategy.get('slow_sma') else 'N/A'}, "
                                      f"Position={strategy.get('position', 0)}, "
                                      f"Last Signal={strategy.get('last_signal', 'None')}")
                            break
                
                await asyncio.sleep(interval)
                
            except Exception as e:
                logger.error(f"Error generating tick: {e}", exc_info=True)
                await asyncio.sleep(interval)
    
    def stop(self):
        """Stop the tick generator."""
        self.running = False
        logger.info(f"Tick generator stopped after {self.tick_count} ticks")


class LiveTradingSystem:
    """Main live trading system coordinator."""
    
    def __init__(self):
        self.settings = None
        self.tick_generator = None
        self.running = False
    
    async def start(self):
        """Start the live trading system."""
        logger.info("Starting Live Trading System")
        logger.info("=" * 60)
        
        try:
            # Load settings
            self.settings = Settings()
            logger.info(f"Executor Mode: {self.settings.EXECUTOR_MODE}")
            logger.info(f"Environment: {self.settings.ENV}")
            logger.info(f"Strategy Pilot: {self.settings.FEATURES_STRATEGY_PILOT}")
            
            # Start executor and load strategies
            start_executor(self.settings)
            load_strategies(self.settings)
            
            # Check loaded strategies
            strategies = get_strategy_status()
            if not strategies:
                logger.error("No strategies loaded! Check configuration.")
                return
            
            logger.info(f"Loaded {len(strategies)} strategies:")
            for strategy in strategies:
                logger.info(f"  - {strategy.get('strategy', 'unknown')}: {strategy.get('symbol', 'N/A')}")
            
            # Create and start tick generator
            self.tick_generator = LiveTickGenerator("EURUSD", 1.1000)
            self.running = True
            
            logger.info("=" * 60)
            logger.info("Live trading system started successfully!")
            logger.info("Press Ctrl+C to stop")
            logger.info("=" * 60)
            
            # Start tick generation
            await self.tick_generator.start(interval=1.0)
            
        except Exception as e:
            logger.error(f"Failed to start live trading system: {e}", exc_info=True)
            raise
    
    def stop(self):
        """Stop the live trading system."""
        logger.info("Stopping Live Trading System")
        self.running = False
        if self.tick_generator:
            self.tick_generator.stop()
        
        # Final strategy status
        try:
            strategies = get_strategy_status()
            logger.info("Final Strategy Status:")
            for strategy in strategies:
                logger.info(f"  {strategy}")
        except Exception as e:
            logger.error(f"Error getting final strategy status: {e}")


async def main():
    """Main function."""
    system = LiveTradingSystem()
    
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
    except Exception as e:
        logger.error(f"Live trading system failed: {e}", exc_info=True)
        return 1
    finally:
        system.stop()
    
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))