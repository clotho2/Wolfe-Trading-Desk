#!/usr/bin/env python3
"""Simple tick generator for testing strategies.

This script generates simulated market ticks for EURUSD and feeds them
to the active strategies. It's designed for testing and development.
"""

import asyncio
import logging
import random
import time
from datetime import datetime, timezone
from typing import Optional

from config.settings import Settings
from core.executor.loop import process_tick, get_strategy_status
from strategies.pilot_sma import Tick

logger = logging.getLogger(__name__)


class TickGenerator:
    """Generates simulated market ticks for testing strategies."""
    
    def __init__(self, symbol: str = "EURUSD", base_price: float = 1.1000):
        self.symbol = symbol
        self.base_price = base_price
        self.current_price = base_price
        self.running = False
        
    def generate_tick(self) -> Tick:
        """Generate a realistic tick with bid/ask spread."""
        # Simulate price movement with some volatility
        change = random.uniform(-0.0005, 0.0005)  # ±5 pips
        self.current_price += change
        
        # Ensure price stays within reasonable bounds
        self.current_price = max(1.0500, min(1.1500, self.current_price))
        
        # Create bid/ask spread (typically 1-2 pips for major pairs)
        spread = random.uniform(0.0001, 0.0002)
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
        logger.info(f"Starting tick generator for {self.symbol} (interval: {interval}s)")
        
        tick_count = 0
        while self.running:
            try:
                tick = self.generate_tick()
                process_tick(tick)
                tick_count += 1
                
                if tick_count % 10 == 0:
                    logger.debug(f"Generated {tick_count} ticks, current price: {tick.bid}/{tick.ask}")
                
                await asyncio.sleep(interval)
                
            except Exception as e:
                logger.error(f"Error generating tick: {e}", exc_info=True)
                await asyncio.sleep(interval)
    
    def stop(self):
        """Stop the tick generator."""
        self.running = False
        logger.info("Tick generator stopped")


async def main():
    """Main function to run the tick generator."""
    # Set up logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Load settings and strategies
    settings = Settings()
    from core.executor.loop import load_strategies
    load_strategies(settings)
    
    # Check if strategies are loaded
    strategies = get_strategy_status()
    if not strategies:
        logger.warning("No strategies loaded. Check configuration.")
        return
    
    logger.info(f"Loaded {len(strategies)} strategies: {[s.get('strategy', 'unknown') for s in strategies]}")
    
    # Start tick generator
    generator = TickGenerator()
    
    try:
        # Generate ticks every 2 seconds for testing
        await generator.start(interval=2.0)
    except KeyboardInterrupt:
        logger.info("Received interrupt signal")
    finally:
        generator.stop()


if __name__ == "__main__":
    asyncio.run(main())