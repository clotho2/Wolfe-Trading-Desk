# path: server/api/ha.py
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, Header, HTTPException
from redis.asyncio import Redis

from config.settings import settings
from infra.ha.ack import set_ack

router = APIRouter(prefix="/ha", tags=["ha"])


def require_token(authorization: Optional[str] = Header(None)):
    token = (authorization or "").removeprefix("Bearer ").strip()
    if token != settings.DASH_TOKEN:
        raise HTTPException(status_code=401, detail="Unauthorized")
    return True


@router.post("/ack", dependencies=[Depends(require_token)])
async def ha_ack():
    r = Redis.from_url(settings.REDIS_URL_EFFECTIVE)
    ts = await set_ack(r)
    return {"status": "ok", "ack": ts}
