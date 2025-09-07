# path: shared/events/bus.py
from __future__ import annotations

import json
import os
import threading
import time
from dataclasses import dataclass, asdict
from typing import Any, Dict, List

_LOG_PATH = os.environ.get("EVENT_LOG_PATH", "logs/events.jsonl")


@dataclass
class Event:
    ts: float
    reason: str
    payload: Dict[str, Any]


class _Bus:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._events: List[Event] = []

    def emit(self, reason: str, **payload: Any) -> None:
        e = Event(time.time(), reason, payload)
        with self._lock:
            self._events.append(e)
            try:
                os.makedirs(os.path.dirname(_LOG_PATH), exist_ok=True)
                with open(_LOG_PATH, "a", encoding="utf-8") as fh:
                    fh.write(json.dumps({"ts": e.ts, "reason": e.reason, "payload": e.payload}) + "\n")
            except Exception:
                # Observability only; never fail caller
                pass

    def drain(self) -> List[Event]:
        with self._lock:
            out = self._events[:]
            self._events.clear()
            return out


bus = _Bus()


async def publish(event_data: dict) -> None:
    """Publish an event to the bus.
    
    Args:
        event_data: Dictionary containing 'evt' and 'payload' keys
    """
    evt = event_data.get("evt", "UNKNOWN")
    payload = event_data.get("payload", {})
    bus.emit(evt, **payload)
