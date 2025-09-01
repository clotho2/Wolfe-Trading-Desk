# path: ops/ha/bootstrap.py
from __future__ import annotations

import asyncio
from typing import Optional

from redis.asyncio import Redis

from config.settings import Settings
from infra.ha.leader import LeaderElector
from shared.events.bus import publish

_elector: Optional[LeaderElector] = None


async def start_ha(app, settings: Settings) -> None:
    """Idempotent HA bootstrap; called from app startup."""
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
        # Executor will handle FLAT_ALL + LOCKDOWN=SPLIT_BRAIN
        await publish({"evt": "HA_LOCK_LOST", "payload": {}})

    _elector.on_gain = on_lock_gain
    _elector.on_loss = on_lock_loss

    app.state.ha = _elector
    asyncio.create_task(_elector.start())


def status() -> dict:
    """Lightweight status for dashboard polling."""
    if not _elector:
        return {"running": False}
    return {
        "running": True,
        "leader": _elector.is_leader,
        "token": _elector.token,
        "ttl_ms": _elector.ttl_ms,
        "hb_ms": _elector.heartbeat_ms,
    }
