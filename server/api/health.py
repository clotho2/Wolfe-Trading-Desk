# path: server/api/health.py
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter

from ops.ha.bootstrap import status as ha_status

router = APIRouter()


@router.get("/health")
async def health():
    s = ha_status()
    token_tail = s.get("token_tail") if s.get("token_tail") else None
    return {"status": "ok", "leader": s.get("leader", False), "token_tail": token_tail}
