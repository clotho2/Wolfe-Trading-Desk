# path: ops/dashboard/app.py (mount nuclear router)
from server.api.nuclear import router as nuclear_router

app.include_router(nuclear_router)


# path: security/nuclear_control.py  (helper to ENGAGE nuclear)
from __future__ import annotations

from typing import Any, List

from config.settings import settings
from ops.audit.immutable_audit import append_event
from shared.services.registry import get_adapter as get_adapter_legacy
from core.executor.registry import get_adapter
from shared.state.nuclear import engage as engage_nuclear, is_active
from shared.state.runtime import LockdownState, get_lockdown, set_lockdown


async def engage(reason: str = "nuclear") -> List[dict]:
    if is_active():
        return []
    engage_nuclear()
    if get_lockdown() != LockdownState.SPLIT_BRAIN:
        set_lockdown(LockdownState.SPLIT_BRAIN)
    # Try both registries for compatibility
    adapter = get_adapter("mt5") or get_adapter_legacy()
    results: List[dict] = []
    if adapter is not None:
        results = await adapter.flat_all("nuclear")
    append_event({"evt": "NUCLEAR_LOCKED", "payload": {"mode": getattr(settings.EXECUTOR_MODE, "value", str(settings.EXECUTOR_MODE)), "count": len(results)}})
    return results


# --------------------------------- TESTS ------------------------------------
# path: tests/executor/test_bootstrap.py
import os
import types

from config.settings import Settings, ExecutorMode
from core.executor.bootstrap import start_executor
from core.executor.registry import get_adapter


def test_bootstrap_registers_once(monkeypatch):
    s = Settings()
    s.EXECUTOR_MODE = ExecutorMode.DRY_RUN
    start_executor(s)
    a1 = get_adapter("mt5")
    start_executor(s)
    a2 = get_adapter("mt5")
    assert a1 is a2


def test_bootstrap_registry_contains_mt5(monkeypatch):
    s = Settings()
    s.EXECUTOR_MODE = ExecutorMode.DRY_RUN
    start_executor(s)
    assert get_adapter("mt5") is not None


def test_bootstrap_safety_blocks_live(monkeypatch):
    s = Settings()
    s.EXECUTOR_MODE = ExecutorMode.LIVE
    monkeypatch.setenv("SAFETY_NO_LIVE", "1")
    try:
        start_executor(s)
        assert False, "Expected AssertionError when SAFETY_NO_LIVE=1 and LIVE"
    except AssertionError:
        pass
