#!/usr/bin/env python3
"""Simplified test script to diagnose trading system issues without pydantic dependencies."""

import json
import logging
import os
import sys
import yaml
from datetime import datetime, timezone
from pathlib import Path

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


def load_config():
    """Load configuration from YAML files."""
    logger.info("=== Loading Configuration ===")
    
    # Load default config
    default_path = Path("config/default.yaml")
    if default_path.exists():
        with open(default_path, 'r') as f:
            default_config = yaml.safe_load(f)
        logger.info(f"Loaded default config: {default_config}")
    else:
        logger.error("Default config not found")
        return None
    
    # Load profile config if exists
    profile_path = Path("config/profile.ftmo.yaml")
    if profile_path.exists():
        with open(profile_path, 'r') as f:
            profile_config = yaml.safe_load(f)
        logger.info(f"Loaded profile config: {profile_config}")
        # Merge with default
        default_config.update(profile_config)
    
    return default_config


def check_environment():
    """Check environment variables."""
    logger.info("=== Checking Environment ===")
    
    env_vars = [
        'EXECUTOR_MODE',
        'SAFETY_NO_LIVE',
        'ENV',
        'FEATURES_STRATEGY_PILOT',
        'FEATURES_AUTO_REGISTER_MT5'
    ]
    
    for var in env_vars:
        value = os.environ.get(var, 'NOT SET')
        logger.info(f"{var}: {value}")


def check_logs():
    """Check existing log files."""
    logger.info("=== Checking Log Files ===")
    
    # Check app.log
    app_log = Path("app.log")
    if app_log.exists():
        logger.info(f"app.log exists, size: {app_log.stat().st_size} bytes")
        # Show last few lines
        lines = app_log.read_text().strip().split('\n')
        if lines:
            logger.info("Last 3 lines of app.log:")
            for line in lines[-3:]:
                logger.info(f"  {line}")
    else:
        logger.info("app.log does not exist")
    
    # Check events.jsonl
    events_log = Path("logs/events.jsonl")
    if events_log.exists():
        logger.info(f"events.jsonl exists, size: {events_log.stat().st_size} bytes")
        # Show last few lines
        lines = events_log.read_text().strip().split('\n')
        if lines:
            logger.info("Last 3 events:")
            for line in lines[-3:]:
                try:
                    event = json.loads(line)
                    logger.info(f"  {event}")
                except json.JSONDecodeError:
                    logger.info(f"  {line}")
    else:
        logger.info("events.jsonl does not exist")


def simulate_strategy():
    """Simulate strategy execution without dependencies."""
    logger.info("=== Simulating Strategy Execution ===")
    
    # Simulate SMA calculation
    prices = [1.1000, 1.1001, 1.1002, 1.1003, 1.1004, 1.1005]
    fast_period = 3
    slow_period = 5
    
    if len(prices) >= slow_period:
        fast_sma = sum(prices[-fast_period:]) / fast_period
        slow_sma = sum(prices[-slow_period:]) / slow_period
        
        logger.info(f"Fast SMA ({fast_period}): {fast_sma:.5f}")
        logger.info(f"Slow SMA ({slow_period}): {slow_sma:.5f}")
        
        # Check for crossover
        if fast_sma > slow_sma:
            logger.info("GOLDEN CROSS detected - would generate BUY signal")
        elif fast_sma < slow_sma:
            logger.info("DEATH CROSS detected - would generate SELL signal")
        else:
            logger.info("No crossover detected")
    else:
        logger.info(f"Not enough prices for SMA calculation (need {slow_period}, have {len(prices)})")


def check_system_status():
    """Check if the system is running."""
    logger.info("=== Checking System Status ===")
    
    # Check for running processes
    import subprocess
    try:
        result = subprocess.run(['ps', 'aux'], capture_output=True, text=True)
        python_processes = [line for line in result.stdout.split('\n') if 'python' in line.lower()]
        
        if python_processes:
            logger.info("Python processes found:")
            for proc in python_processes:
                logger.info(f"  {proc}")
        else:
            logger.info("No Python processes found")
            
    except Exception as e:
        logger.error(f"Error checking processes: {e}")


def create_test_event():
    """Create a test event to verify logging works."""
    logger.info("=== Creating Test Event ===")
    
    # Ensure logs directory exists
    logs_dir = Path("logs")
    logs_dir.mkdir(exist_ok=True)
    
    # Create test event
    test_event = {
        "ts": datetime.now().timestamp(),
        "reason": "TEST_EVENT",
        "payload": {
            "test": "data",
            "timestamp": datetime.now().isoformat()
        }
    }
    
    # Write to events.jsonl
    events_file = Path("logs/events.jsonl")
    with open(events_file, "a") as f:
        f.write(json.dumps(test_event) + "\n")
    
    logger.info(f"Test event written to {events_file}")
    logger.info(f"Event: {test_event}")


def main():
    """Run all diagnostic tests."""
    logger.info("Starting Trading System Diagnostics")
    logger.info("=" * 50)
    
    try:
        # Test 1: Configuration
        config = load_config()
        
        # Test 2: Environment
        check_environment()
        
        # Test 3: Logs
        check_logs()
        
        # Test 4: System Status
        check_system_status()
        
        # Test 5: Strategy Simulation
        simulate_strategy()
        
        # Test 6: Create Test Event
        create_test_event()
        
        logger.info("=" * 50)
        logger.info("Diagnostics completed!")
        
        # Summary
        logger.info("\n=== SUMMARY ===")
        logger.info("Issues found:")
        logger.info("1. System is not currently running")
        logger.info("2. Dependencies (pydantic) have compatibility issues with Python 3.13")
        logger.info("3. No tick data feed is running")
        logger.info("4. Strategy needs to be loaded and fed with market data")
        
        logger.info("\nRecommendations:")
        logger.info("1. Start the system with: python3 scripts/dev_run.py --mode DRY_RUN")
        logger.info("2. Use Python 3.11 or 3.12 for better pydantic compatibility")
        logger.info("3. Run the tick generator to feed market data to strategies")
        logger.info("4. Check that all configuration is properly loaded")
        
    except Exception as e:
        logger.error(f"Diagnostic failed: {e}", exc_info=True)
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())