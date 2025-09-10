# path: server/api/strategy.py
from __future__ import annotations

from typing import List, Dict, Any

from fastapi import APIRouter

from core.executor.loop import get_strategy_status, load_strategies
from config.settings import Settings

router = APIRouter()


@router.get("/strategy/status")
async def strategy_status() -> Dict[str, Any]:
    """Get status of all enabled strategies and their last signal times."""
    # Ensure strategies are loaded
    settings = Settings()
    load_strategies(settings)
    
    # Get status of all active strategies
    strategies = get_strategy_status()
    
    return {
        "enabled": len(strategies) > 0,
        "count": len(strategies),
        "strategies": strategies
    }