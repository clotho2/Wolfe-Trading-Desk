# path: ops/ha/handler.py
from __future__ import annotations

from typing import Any, List

from config.settings import settings
from shared.events.bus import publish
from shared.state.runtime import LockdownState, get_lockdown, set_lockdown


async def handle_ha_lock_lost(adapter: Any) -> List[dict]:
    """Executor hook for HA split-brain.

    Idempotent; emits FLAT_ALL_EXECUTED once and sets LOCKDOWN=SPLIT_BRAIN.
    Feature-gated via settings.FEATURES_HA_DRILLS.
    """
    if not getattr(settings, "FEATURES_HA_DRILLS", False):
        return []

    if get_lockdown() == LockdownState.SPLIT_BRAIN:
        return []

    results = await adapter.flat_all("split_brain")
    await publish({
        "evt": "FLAT_ALL_EXECUTED",
        "payload": {
            "mode": getattr(settings.EXECUTOR_MODE, "value", str(settings.EXECUTOR_MODE)),
            "count": len(results),
        },
    })
    set_lockdown(LockdownState.SPLIT_BRAIN)
    return results
