from __future__ import annotations

import json
import logging
import threading
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Callable, Dict, List, Optional

import zmq


logger = logging.getLogger(__name__)


@dataclass
class BridgeConfig:
    host: str
    pub_port: int
    req_port: int
    token: str
    symbols: List[str]


class MT5ZMQClient:
    """ZeroMQ client that connects to the MT5 bridge server.

    Responsibilities:
    - Maintain a SUB socket to receive ticks from the bridge and call on_tick
    - Provide a synchronous REQ method to place orders and perform actions
    - Handle reconnects and report basic health metrics
    """

    def __init__(self, config: BridgeConfig, on_tick: Callable[[str, float, float, datetime], None]):
        self.config = config
        self.on_tick = on_tick

        self._ctx: Optional[zmq.Context] = None
        self._sub: Optional[zmq.Socket] = None
        self._req: Optional[zmq.Socket] = None
        self._sub_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()

        self._last_tick_at: Optional[datetime] = None
        self._connected = False

    # ---- lifecycle ----
    def start(self) -> None:
        self._ctx = zmq.Context.instance()

        # REQ setup
        self._req = self._ctx.socket(zmq.REQ)
        self._req.linger = 0
        self._req.rcvtimeo = 3000
        self._req.sndtimeo = 3000
        req_url = f"tcp://{self.config.host}:{self.config.req_port}"
        self._req.connect(req_url)

        # SUB setup
        self._sub = self._ctx.socket(zmq.SUB)
        self._sub.linger = 0
        self._sub.rcvtimeo = 1000
        sub_url = f"tcp://{self.config.host}:{self.config.pub_port}"
        self._sub.connect(sub_url)
        # Subscribe to all and filter in software for token/symbols
        self._sub.setsockopt_string(zmq.SUBSCRIBE, "")

        # Try a health request to confirm connectivity
        try:
            _ = self.health()
            self._connected = True
            logger.info(f"Bridge REQ connected: {req_url}")
        except Exception as e:
            logger.warning(f"Bridge REQ not reachable yet: {e}")

        # Start SUB thread
        self._stop_event.clear()
        self._sub_thread = threading.Thread(target=self._sub_loop, name="mt5-bridge-sub", daemon=True)
        self._sub_thread.start()
        logger.info(f"Bridge SUB started: {sub_url}; symbols={self.config.symbols}")

    def stop(self) -> None:
        self._stop_event.set()
        if self._sub_thread and self._sub_thread.is_alive():
            self._sub_thread.join(timeout=2.0)
        try:
            if self._sub is not None:
                self._sub.close(0)
        finally:
            self._sub = None
        try:
            if self._req is not None:
                self._req.close(0)
        finally:
            self._req = None
        if self._ctx is not None:
            # Do not terminate global instance; just drop references
            self._ctx = None

    # ---- public API ----
    def health(self) -> Dict:
        payload = {"token": self.config.token, "action": "health"}
        resp = self._send_req(payload)
        return resp or {"ok": False}

    def place_order(self, symbol: str, side: str, qty: float, meta: Optional[Dict] = None) -> Dict:
        payload = {
            "token": self.config.token,
            "action": "order_send",
            "symbol": symbol,
            "side": side,
            "qty": qty,
            "meta": meta or {},
        }
        return self._send_req(payload) or {"ok": False, "error": "no_response"}

    def close_all(self, reason: str = "user") -> Dict:
        payload = {"token": self.config.token, "action": "close_all", "reason": reason}
        return self._send_req(payload) or {"ok": False}

    def positions(self) -> Dict:
        payload = {"token": self.config.token, "action": "positions"}
        return self._send_req(payload) or {"ok": False, "positions": []}

    # ---- internals ----
    def _send_req(self, msg: Dict, retries: int = 2) -> Optional[Dict]:
        if self._req is None:
            raise RuntimeError("REQ socket not initialized")
        last_exc: Optional[Exception] = None
        for _ in range(retries):
            try:
                self._req.send_string(json.dumps(msg))
                reply = self._req.recv_string()
                return json.loads(reply)
            except Exception as e:
                last_exc = e
                time.sleep(0.2)
                continue
        if last_exc:
            logger.warning(f"Bridge request failed: {last_exc}")
        return None

    def _sub_loop(self) -> None:
        assert self._sub is not None
        symbols_set = {s.upper() for s in self.config.symbols}

        while not self._stop_event.is_set():
            try:
                msg = self._sub.recv_string(flags=0)
            except zmq.Again:
                continue
            except Exception as e:
                if not self._stop_event.is_set():
                    logger.warning(f"Bridge SUB error: {e}")
                time.sleep(0.5)
                continue

            try:
                data = json.loads(msg)
                if data.get("token") != self.config.token:
                    continue
                symbol = str(data.get("symbol", "")).upper()
                if symbols_set and symbol not in symbols_set:
                    continue
                bid = float(data.get("bid"))
                ask = float(data.get("ask"))
                ts = data.get("timestamp") or data.get("ts")
                if isinstance(ts, (int, float)):
                    dt = datetime.fromtimestamp(float(ts), tz=timezone.utc)
                else:
                    dt = datetime.fromisoformat(ts.replace("Z", "+00:00")) if ts else datetime.now(timezone.utc)

                self._last_tick_at = dt
                # Call back into the adapter to forward to strategies
                try:
                    self.on_tick(symbol, bid, ask, dt)
                except Exception as cb_err:
                    logger.error(f"on_tick callback failed: {cb_err}")

            except Exception as parse_err:
                logger.debug(f"Bridge SUB parse error: {parse_err}")

    # ---- metrics ----
    @property
    def last_tick_at(self) -> Optional[datetime]:
        return self._last_tick_at

    @property
    def is_connected(self) -> bool:
        return bool(self._connected)

