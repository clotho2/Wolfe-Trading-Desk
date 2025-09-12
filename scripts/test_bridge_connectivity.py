#!/usr/bin/env python3

from __future__ import annotations

import os
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from adapters.mt5.bridge_client import MT5ZMQClient, BridgeConfig


def main() -> int:
    host = os.getenv("BRIDGE_HOST", "127.0.0.1")
    pub_port = int(os.getenv("BRIDGE_PUB_PORT", "5556"))
    req_port = int(os.getenv("BRIDGE_REQ_PORT", "5557"))
    token = os.getenv("BRIDGE_TOKEN", "change-me")
    symbols = [s.strip().upper() for s in os.getenv("WATCHLIST", "EURUSD").split(",") if s.strip()]

    cfg = BridgeConfig(host=host, pub_port=pub_port, req_port=req_port, token=token, symbols=symbols)

    ticks = []

    def on_tick(symbol: str, bid: float, ask: float, ts: datetime) -> None:
        ticks.append((symbol, bid, ask, ts))
        print(f"tick {symbol} {bid:.5f}/{ask:.5f} {ts.isoformat()}")

    client = MT5ZMQClient(cfg, on_tick=on_tick)
    client.start()

    try:
        print("Health:", client.health())
        print("Waiting for 5 ticks...")
        import time
        deadline = time.time() + 10
        while time.time() < deadline and len(ticks) < 5:
            time.sleep(0.2)
        print(f"Received {len(ticks)} ticks")
        if not ticks:
            print("No ticks received. Check ports, token, and that the bridge server is running.")
            return 2
        print("Sending DRY order (0.01 BUY EURUSD) via bridge...")
        print(client.place_order("EURUSD", "BUY", 0.01))
    finally:
        client.stop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

