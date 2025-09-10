#!/usr/bin/env python3
"""Test script to verify trading system functionality.

This script tests the complete trading pipeline:
1. Configuration loading
2. Strategy loading
3. Adapter registration
4. Tick processing
5. Trade execution and logging
"""

import logging
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

# Add the workspace root to Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

from config.settings import Settings
from core.executor.bootstrap import start_executor
from core.executor.loop import load_strategies, get_strategy_status, process_tick
from core.executor.registry import get_adapter
from strategies.pilot_sma import Tick, PilotSMAStrategy

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


def test_configuration():
    """Test configuration loading and settings."""
    logger.info("=== Testing Configuration ===")
    
    settings = Settings()
    
    logger.info(f"Executor Mode: {settings.EXECUTOR_MODE}")
    logger.info(f"Environment: {settings.ENV}")
    logger.info(f"Strategy Pilot Feature: {settings.FEATURES_STRATEGY_PILOT}")
    logger.info(f"Auto Register MT5: {settings.FEATURES_AUTO_REGISTER_MT5}")
    logger.info(f"Watchlist: {settings.watchlist}")
    
    # Check strategy configuration
    if hasattr(settings, 'strategies') and hasattr(settings.strategies, 'enabled'):
        logger.info(f"Enabled Strategies: {settings.strategies.enabled}")
        if hasattr(settings.strategies, 'pilot_sma'):
            logger.info(f"Pilot SMA Config: {settings.strategies.pilot_sma}")
    
    return settings


def test_adapter_registration(settings):
    """Test adapter registration and status."""
    logger.info("=== Testing Adapter Registration ===")
    
    # Start executor to register adapters
    start_executor(settings)
    
    # Check if MT5 adapter is registered
    mt5_adapter = get_adapter("mt5")
    if mt5_adapter:
        logger.info("MT5 Adapter registered successfully")
        status = mt5_adapter.get_status()
        logger.info(f"MT5 Adapter Status: {status}")
        return mt5_adapter
    else:
        logger.error("MT5 Adapter not registered")
        return None


def test_strategy_loading(settings):
    """Test strategy loading and instantiation."""
    logger.info("=== Testing Strategy Loading ===")
    
    # Load strategies
    load_strategies(settings)
    
    # Check loaded strategies
    strategies = get_strategy_status()
    logger.info(f"Loaded {len(strategies)} strategies")
    
    for strategy in strategies:
        logger.info(f"Strategy: {strategy}")
    
    return strategies


def test_tick_processing():
    """Test tick processing through strategies."""
    logger.info("=== Testing Tick Processing ===")
    
    # Create test ticks
    test_ticks = [
        Tick("EURUSD", 1.1000, 1.1002, datetime.now(timezone.utc)),
        Tick("EURUSD", 1.1001, 1.1003, datetime.now(timezone.utc)),
        Tick("EURUSD", 1.1002, 1.1004, datetime.now(timezone.utc)),
        Tick("EURUSD", 1.1003, 1.1005, datetime.now(timezone.utc)),
        Tick("EURUSD", 1.1004, 1.1006, datetime.now(timezone.utc)),
    ]
    
    logger.info("Processing test ticks...")
    for i, tick in enumerate(test_ticks):
        logger.info(f"Processing tick {i+1}: {tick.symbol} {tick.bid}/{tick.ask}")
        process_tick(tick)
    
    # Check strategy status after processing ticks
    strategies = get_strategy_status()
    for strategy in strategies:
        if strategy.get('strategy') == 'pilot_sma':
            logger.info(f"Pilot SMA Status: {strategy}")


def test_direct_strategy():
    """Test strategy directly without the loop system."""
    logger.info("=== Testing Direct Strategy ===")
    
    settings = Settings()
    strategy = PilotSMAStrategy(settings)
    
    # Generate enough ticks to trigger SMA calculations
    base_price = 1.1000
    for i in range(60):  # Generate 60 ticks to fill the slow SMA buffer
        price = base_price + (i * 0.0001)  # Gradual upward trend
        tick = Tick("EURUSD", price, price + 0.0002, datetime.now(timezone.utc))
        strategy.on_tick(tick)
        
        if i % 10 == 0:
            status = strategy.get_status()
            logger.info(f"Tick {i}: Price={price:.5f}, Fast SMA={status.get('fast_sma')}, Slow SMA={status.get('slow_sma')}")
    
    # Final status
    final_status = strategy.get_status()
    logger.info(f"Final Strategy Status: {final_status}")


def test_trade_logging():
    """Test trade logging functionality."""
    logger.info("=== Testing Trade Logging ===")
    
    # Check if events.jsonl exists and has recent entries
    events_file = Path("logs/events.jsonl")
    if events_file.exists():
        logger.info(f"Events file exists: {events_file}")
        
        # Read last few lines
        lines = events_file.read_text().strip().split('\n')
        if lines:
            logger.info(f"Total events: {len(lines)}")
            logger.info("Last 3 events:")
            for line in lines[-3:]:
                logger.info(f"  {line}")
        else:
            logger.info("Events file is empty")
    else:
        logger.info("Events file does not exist")


def main():
    """Run all tests."""
    logger.info("Starting Trading System Tests")
    logger.info("=" * 50)
    
    try:
        # Test 1: Configuration
        settings = test_configuration()
        
        # Test 2: Adapter Registration
        adapter = test_adapter_registration(settings)
        
        # Test 3: Strategy Loading
        strategies = test_strategy_loading(settings)
        
        # Test 4: Tick Processing
        test_tick_processing()
        
        # Test 5: Direct Strategy Test
        test_direct_strategy()
        
        # Test 6: Trade Logging
        test_trade_logging()
        
        logger.info("=" * 50)
        logger.info("All tests completed successfully!")
        
    except Exception as e:
        logger.error(f"Test failed: {e}", exc_info=True)
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())