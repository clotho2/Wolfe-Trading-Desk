# path: ops/ha/bootstrap.py (enhance status payload)
from __future__ import annotations

import asyncio
import time
from typing import Optional

from redis.asyncio import Redis

from config.settings import Settings
from infra.ha.leader import LeaderElector
from shared.events.bus import publish

_elector: Optional[LeaderElector] = None


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
        await publish({"evt": "HA_LOCK_LOST", "payload": {}})

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
