# path: tests/drills/test_ha_split_brain.py
import os
import types
import asyncio
import pytest

from config.settings import settings, ExecutorMode
from adapters.mt5.mt5_adapter import MT5Adapter, _Position
from ops.ha.handler import handle_ha_lock_lost
from shared.state.runtime import set_lockdown, LockdownState, get_lockdown


@pytest.fixture(autouse=True)
def _safety_env(monkeypatch):
    monkeypatch.setenv("SAFETY_NO_LIVE", "1")
    yield


@pytest.fixture(autouse=True)
def _enable_ha_drills(monkeypatch):
    monkeypatch.setattr(settings, "FEATURES_HA_DRILLS", True, raising=False)
    set_lockdown(LockdownState.NONE)
    yield
    set_lockdown(LockdownState.NONE)


async def _mk_adapter(mode: ExecutorMode, positions=2):
    a = MT5Adapter()
    # mode override for tests
    a.settings.EXECUTOR_MODE = mode
    async def list_positions():
        return [_Position(symbol=f"SYM{i}", ticket=100+i) for i in range(positions)]
    async def close_pos(p: _Position):
        return True
    a.list_open_positions = types.MethodType(lambda self: list_positions(), a)  # type: ignore[attr-defined]
    a.close_position = types.MethodType(lambda self, p: close_pos(p), a)  # type: ignore[attr-defined]
    return a


@pytest.mark.asyncio
async def test_split_brain_shadow_flat_all(monkeypatch):
    a = await _mk_adapter(ExecutorMode.SHADOW)
    events = []
    async def fake_publish(evt):
        events.append(evt)
    monkeypatch.setattr("shared.events.bus.publish", "__call__", fake_publish, raising=False)
    # monkeypatch module function directly
    monkeypatch.setattr("shared.events.bus.publish", fake_publish)

    res = await handle_ha_lock_lost(a)
    assert len(res) == 2 and all(r["status"] == "shadow" for r in res)
    assert get_lockdown() == LockdownState.SPLIT_BRAIN
    assert any(e.get("evt") == "FLAT_ALL_EXECUTED" for e in events)


@pytest.mark.asyncio
async def test_split_brain_dry_run_flat_all(monkeypatch):
    a = await _mk_adapter(ExecutorMode.DRY_RUN)
    events = []
    monkeypatch.setattr("shared.events.bus.publish", lambda evt: events.append(evt))
    res = await handle_ha_lock_lost(a)
    assert len(res) == 2 and all(r["status"] == "skip" for r in res)
    assert get_lockdown() == LockdownState.SPLIT_BRAIN
    assert any(e.get("evt") == "FLAT_ALL_EXECUTED" for e in events)


@pytest.mark.asyncio
async def test_split_brain_live_flat_all(monkeypatch):
    a = await _mk_adapter(ExecutorMode.LIVE)
    called = {"count": 0}
    async def close_pos(p: _Position):
        called["count"] += 1
        return True
    a.close_position = types.MethodType(lambda self, p: close_pos(p), a)  # type: ignore[attr-defined]

    events = []
    monkeypatch.setattr("shared.events.bus.publish", lambda evt: events.append(evt))

    res = await handle_ha_lock_lost(a)
    assert len(res) == 2 and all(r["status"] == "closed" for r in res)
    assert called["count"] == 2
    assert get_lockdown() == LockdownState.SPLIT_BRAIN
    assert any(e.get("evt") == "FLAT_ALL_EXECUTED" for e in events)


@pytest.mark.asyncio
async def test_split_brain_idempotent(monkeypatch):
    a = await _mk_adapter(ExecutorMode.SHADOW)
    events = []
    monkeypatch.setattr("shared.events.bus.publish", lambda evt: events.append(evt))

    res1 = await handle_ha_lock_lost(a)
    res2 = await handle_ha_lock_lost(a)  # second event ignored

    assert len(res1) == 2 and len(res2) == 0
    assert sum(1 for e in events if e.get("evt") == "FLAT_ALL_EXECUTED") == 1
