# path: server/api/adapter.py
from __future__ import annotations

from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse

from core.executor.registry import get_adapter

router = APIRouter(prefix="/adapter", tags=["adapter"])


@router.get("/mt5/status")
async def mt5_status():
    """Get MT5 adapter status including connection info and last tick."""
    adapter = get_adapter("mt5")
    
    if not adapter:
        raise HTTPException(status_code=404, detail="MT5 adapter not registered")
    
    if not hasattr(adapter, 'get_status'):
        # Fallback for older adapter versions
        return JSONResponse(content={
            "connected": False,
            "server": "",
            "login": "",
            "last_tick": None,
            "error": "Adapter does not support status reporting"
        })
    
    try:
        status = adapter.get_status()
        return JSONResponse(content=status)
    except Exception as e:
        return JSONResponse(content={
            "connected": False,
            "error": str(e)
        }, status_code=500)