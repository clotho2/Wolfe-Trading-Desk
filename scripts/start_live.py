#!/usr/bin/env python3
"""Start the live trading system with proper environment configuration."""

import os
import subprocess
import sys
from pathlib import Path

def main():
    """Start the live trading system."""
    print("Starting WolfeDesk Live Trading System")
    print("=" * 50)
    
    # Set environment variables for live trading
    env = os.environ.copy()
    env["EXECUTOR_MODE"] = "LIVE"
    env["SAFETY_NO_LIVE"] = "0"
    env["FEATURES_STRATEGY_PILOT"] = "1"
    env["FEATURES_AUTO_REGISTER_MT5"] = "1"
    env["ENV"] = "dev"
    
    print("Environment Configuration:")
    print(f"  EXECUTOR_MODE: {env['EXECUTOR_MODE']}")
    print(f"  SAFETY_NO_LIVE: {env['SAFETY_NO_LIVE']}")
    print(f"  FEATURES_STRATEGY_PILOT: {env['FEATURES_STRATEGY_PILOT']}")
    print(f"  FEATURES_AUTO_REGISTER_MT5: {env['FEATURES_AUTO_REGISTER_MT5']}")
    print("=" * 50)
    
    # Start the live trading system
    try:
        cmd = [sys.executable, "scripts/live_trading.py"]
        print(f"Executing: {' '.join(cmd)}")
        print("=" * 50)
        
        result = subprocess.run(cmd, env=env, cwd=Path(__file__).parent.parent)
        return result.returncode
        
    except KeyboardInterrupt:
        print("\nReceived interrupt signal")
        return 0
    except Exception as e:
        print(f"Error starting live trading system: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())