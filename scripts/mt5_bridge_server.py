#!/usr/bin/env python3
"""
MT5 Bridge Server (Windows host):

Runs alongside MT5 Terminal on Windows. Requires:
  pip install MetaTrader5 pyzmq

Provides:
  - PUB ticks on tcp://0.0.0.0:<PUB_PORT>
  - REQ/REP commands on tcp://0.0.0.0:<REQ_PORT>

Security:
  - Simple shared token in each message
  - Bind to localhost by default; use firewall when exposing externally
"""

from __future__ import annotations

import json
import logging
import os
import threading
import time
from datetime import datetime, timezone
from typing import Dict, List

import zmq

try:
    import MetaTrader5 as mt5
except ImportError as e:
    raise SystemExit("MetaTrader5 Python module is required on Windows host") from e


logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
logger = logging.getLogger("mt5-bridge")


PUB_HOST = os.getenv("BRIDGE_PUB_HOST", "0.0.0.0")
REQ_HOST = os.getenv("BRIDGE_REQ_HOST", "0.0.0.0")
PUB_PORT = int(os.getenv("BRIDGE_PUB_PORT", "5556"))
REQ_PORT = int(os.getenv("BRIDGE_REQ_PORT", "5557"))
TOKEN = os.getenv("BRIDGE_TOKEN", "change-me")

MT5_SERVER = os.getenv("MT5_SERVER", "")
MT5_LOGIN = os.getenv("MT5_LOGIN", "")
MT5_PASSWORD = os.getenv("MT5_PASSWORD", "")

WATCHLIST = [s.strip().upper() for s in os.getenv("WATCHLIST", "EURUSD,USDCHF,NZDUSD").split(",") if s.strip()]


def init_mt5() -> None:
    if not mt5.initialize():
        raise RuntimeError(f"mt5.initialize failed: {mt5.last_error()}")
    if MT5_LOGIN and MT5_SERVER:
        if not mt5.login(int(MT5_LOGIN), password=MT5_PASSWORD, server=MT5_SERVER):
            raise RuntimeError(f"mt5.login failed: {mt5.last_error()}
")
    logger.info("MT5 initialized")
    for sym in WATCHLIST:
        mt5.symbol_select(sym, True)
    logger.info(f"Watchlist selected: {WATCHLIST}")


def publisher(ctx: zmq.Context) -> None:
    pub = ctx.socket(zmq.PUB)
    pub.linger = 0
    pub.bind(f"tcp://{PUB_HOST}:{PUB_PORT}")
    logger.info(f"PUB bound on tcp://{PUB_HOST}:{PUB_PORT}")

    while True:
        try:
            for sym in WATCHLIST:
                info = mt5.symbol_info_tick(sym)
                if info is None:
                    continue
                msg = {
                    "token": TOKEN,
                    "symbol": sym,
                    "bid": float(info.bid),
                    "ask": float(info.ask),
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                }
                pub.send_string(json.dumps(msg))
            time.sleep(0.2)
        except Exception as e:
            logger.warning(f"publisher error: {e}")
            time.sleep(0.5)


def responder(ctx: zmq.Context) -> None:
    rep = ctx.socket(zmq.REP)
    rep.linger = 0
    rep.bind(f"tcp://{REQ_HOST}:{REQ_PORT}")
    logger.info(f"REP bound on tcp://{REQ_HOST}:{REQ_PORT}")

    while True:
        try:
            req_s = rep.recv_string()
            req = json.loads(req_s)
            if req.get("token") != TOKEN:
                rep.send_string(json.dumps({"ok": False, "error": "unauthorized"}))
                continue

            action = req.get("action")
            if action == "health":
                acc = mt5.account_info()
                rep.send_string(json.dumps({"ok": True, "balance": getattr(acc, 'balance', None)}))
            elif action == "positions":
                pos = mt5.positions_get()
                as_list: List[Dict] = []
                for p in pos or []:
                    as_list.append({
                        "ticket": int(p.ticket),
                        "symbol": str(p.symbol),
                        "type": int(p.type),
                        "volume": float(p.volume),
                        "price_open": float(p.price_open),
                    })
                rep.send_string(json.dumps({"ok": True, "positions": as_list}))
            elif action == "close_all":
                ok_all = True
                for p in mt5.positions_get() or []:
                    side = "SELL" if p.type == 0 else "BUY"  # 0=BUY,1=SELL in MT5; reverse for closing
                    request = {
                        "action": mt5.TRADE_ACTION_DEAL,
                        "symbol": p.symbol,
                        "volume": p.volume,
                        "type": mt5.ORDER_TYPE_SELL if side == "SELL" else mt5.ORDER_TYPE_BUY,
                        "position": p.ticket,
                        "deviation": 10,
                        "magic": 42,
                        "comment": f"bridge-close {req.get('reason','user')}",
                    }
                    res = mt5.order_send(request)
                    ok_all = ok_all and (res is not None and res.retcode == mt5.TRADE_RETCODE_DONE)
                rep.send_string(json.dumps({"ok": ok_all}))
            elif action == "order_send":
                symbol = str(req.get("symbol"))
                side = str(req.get("side", "")).upper()
                qty = float(req.get("qty"))
                mt5.symbol_select(symbol, True)
                order_type = mt5.ORDER_TYPE_BUY if side == "BUY" else mt5.ORDER_TYPE_SELL
                request = {
                    "action": mt5.TRADE_ACTION_DEAL,
                    "symbol": symbol,
                    "volume": qty,
                    "type": order_type,
                    "deviation": 10,
                    "magic": 42,
                    "comment": "bridge-order",
                }
                res = mt5.order_send(request)
                if res is not None and res.retcode == mt5.TRADE_RETCODE_DONE:
                    rep.send_string(json.dumps({"ok": True, "order_id": int(getattr(res, 'order', 0))}))
                else:
                    rep.send_string(json.dumps({"ok": False, "error": str(getattr(res, 'retcode', 'unknown'))}))
            else:
                rep.send_string(json.dumps({"ok": False, "error": "unknown_action"}))
        except Exception as e:
            logger.warning(f"responder error: {e}")
            try:
                rep.send_string(json.dumps({"ok": False, "error": str(e)}))
            except Exception:
                pass


def main() -> int:
    init_mt5()
    ctx = zmq.Context.instance()
    t_pub = threading.Thread(target=publisher, args=(ctx,), daemon=True)
    t_rep = threading.Thread(target=responder, args=(ctx,), daemon=True)
    t_pub.start()
    t_rep.start()
    logger.info("MT5 bridge server started")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("Stopping bridge...")
    finally:
        mt5.shutdown()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

