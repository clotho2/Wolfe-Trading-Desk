# path: shared/events/bus.py
from __future__ import annotations

from typing import Any, Dict

from ops.audit.immutable_audit import append_event


async def publish(evt: Dict[str, Any]) -> None:
    # Simple async facade over immutable audit
    append_event(evt)
