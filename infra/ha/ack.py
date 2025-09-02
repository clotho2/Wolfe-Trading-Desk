# path: infra/ha/ack.py
from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from redis.asyncio import Redis

ACK_HASH = "ha:ack"
ACK_FIELD = "split_brain_ack"


async def set_ack(r: Redis, ts: Optional[datetime] = None) -> str:
    when = (ts or datetime.now(timezone.utc)).isoformat()
    await r.hset(ACK_HASH, ACK_FIELD, when)
    return when


async def get_ack(r: Redis) -> Optional[str]:
    val = await r.hget(ACK_HASH, ACK_FIELD)
    return val.decode() if isinstance(val, (bytes, bytearray)) else val


async def has_ack(r: Redis) -> bool:
    return await r.hexists(ACK_HASH, ACK_FIELD)
