# path: ops/ha/bootstrap.py (wire on_loss → executor hook with debounce/cooldown)
from __future__ import annotations

import asyncio
import time
from typing import Optional

from redis.asyncio import Redis

from config.settings import Settings, settings
from infra.ha.leader import LeaderElector
from ops.ha.handler import handle_ha_lock_lost
from shared.events.bus import publish
from shared.services.registry import get_adapter
from shared.state.runtime import LockdownState, get_lockdown

_elector: Optional[LeaderElector] = None
_last_trigger_ms: Optional[float] = None
_COOLDOWN_MS = 5000


async def start_ha(app, settings: Settings) -> None:
    global _elector
    if _elector:
        return

    r = Redis.from_url(settings.REDIS_URL_EFFECTIVE, health_check_interval=10)
    _elector = LeaderElector(
        redis=r,
        lock_key=settings.HA_LOCK_KEY,
        ttl_ms=settings.LOCK_TTL_MS,
        heartbeat_ms=settings.HEARTBEAT_MS,
        fencing=True,
    )

    async def on_lock_gain(token: int):
        await publish({"evt": "HA_LOCK_GAINED", "payload": {"token": token}})

    async def on_lock_loss():
        # Always emit HA_LOCK_LOST
        await publish({"evt": "HA_LOCK_LOST", "payload": {}})

        # Guard: auto-flat-all feature flag
        if not settings.FEATURES_AUTO_FLAT_ALL_ON_LOCK_LOSS:
            return
        # Guard: idempotent (already in lockdown)
        if get_lockdown() == LockdownState.SPLIT_BRAIN:
            return
        # Guard: cooldown (debounce flapping)
        global _last_trigger_ms
        now_ms = time.time() * 1000
        if _last_trigger_ms and (now_ms - _last_trigger_ms) < _COOLDOWN_MS:
            return
        _last_trigger_ms = now_ms

        adapter = get_adapter()
        if adapter is None:
            await publish({"evt": "HA_AUTO_FLAT_SKIPPED", "payload": {"reason": "no_adapter"}})
            return
        # Execute hook (it will set lockdown + emit FLAT_ALL_EXECUTED)
        await handle_ha_lock_lost(adapter)

    _elector.on_gain = on_lock_gain
    _elector.on_loss = on_lock_loss

    app.state.ha = _elector
    asyncio.create_task(_elector.start())


def status() -> dict:
    if not _elector:
        return {"running": False}
    token = _elector.token
    token_tail = (str(token)[-6:] if token is not None else None)
    last_hb = _elector.last_hb_ts
    last_hb_ms_ago = int((time.time() - last_hb) * 1000) if last_hb else None
    return {
        "running": True,
        "leader": _elector.is_leader,
        "token_tail": token_tail,
        "ttl_ms": _elector.ttl_ms,
        "hb_ms": _elector.heartbeat_ms,
        "last_hb_ms_ago": last_hb_ms_ago,
    }
