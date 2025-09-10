# path: core/executor/bootstrap.py
from __future__ import annotations

import logging
from typing import Optional

from config.settings import Settings
from adapters.mt5.adapter import MT5Adapter
from core.executor.registry import register_adapter, get_adapter

logger = logging.getLogger(__name__)
_adapter: Optional[MT5Adapter] = None


def start_executor(settings: Settings) -> None:
    """Idempotently register MT5 for dev/E2E so HA auto-flat works.
    No broker I/O unless LIVE and safety allows.
    """
    global _adapter
    if get_adapter("mt5") is not None:
        logger.debug("MT5 adapter already registered")
        return
    
    logger.info("Registering MT5 adapter...")
    _adapter = MT5Adapter(settings=settings)
    
    if settings.EXECUTOR_MODE.value == "LIVE":
        _adapter.assert_live_allowed()
    
    register_adapter("mt5", _adapter)
    logger.info(f"MT5 adapter registered successfully (mode={settings.EXECUTOR_MODE.value})")
