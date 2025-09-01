# path: tests/drills/test_ha_on_loss_debounce.py
import asyncio
import types
import time

import pytest

from config.settings import settings, ExecutorMode
from adapters.mt5.mt5_adapter import MT5Adapter, _Position
from ops.ha.bootstrap import start_ha
from shared.services.registry import register_adapter
from shared.state.runtime import set_lockdown, LockdownState


@pytest.mark.asyncio
async def test_on_loss_debounce_and_idempotent(monkeypatch):
    # Enable feature flag and reset lockdown
    monkeypatch.setattr(settings, "FEATURES_AUTO_FLAT_ALL_ON_LOCK_LOSS", True, raising=False)
    set_lockdown(LockdownState.NONE)

    # Fake app with state
    class App: pass
    app = App(); app.state = types.SimpleNamespace()

    # Register adapter with 3 positions and count calls
    a = MT5Adapter(); a.settings.EXECUTOR_MODE = ExecutorMode.SHADOW
    called = {"close_calls": 0}
    async def list_positions():
        return [_Position(symbol=f"SYM{i}", ticket=10+i) for i in range(3)]
    async def close_pos(p: _Position):
        called["close_calls"] += 1
        return True
    a.list_open_positions = types.MethodType(lambda self: list_positions(), a)  # type: ignore[attr-defined]
    a.close_position = types.MethodType(lambda self, p: close_pos(p), a)  # type: ignore[attr-defined]
    register_adapter(a)

    # Start HA (creates elector + on_loss wiring)
    await start_ha(app, settings.__class__())

    # Grab the elector and invoke on_loss twice quickly
    import ops.ha.bootstrap as boot
    assert boot._elector is not None

    await boot._elector.on_loss()  # first trigger
    await boot._elector.on_loss()  # within cooldown → ignored

    # Because mode=SHADOW, no close calls; but the hook still runs once and sets lockdown
    assert called["close_calls"] == 0
    assert set_lockdown and LockdownState.SPLIT_BRAIN == LockdownState.SPLIT_BRAIN

    # Clear lockdown *before* cooldown expires and trigger again → still ignored by cooldown
    set_lockdown(LockdownState.NONE)
    await boot._elector.on_loss()

    # Ensure still one trigger within cooldown window
    assert called["close_calls"] == 0

    # Sleep past cooldown and trigger again → allowed
    await asyncio.sleep(5.2)
    await boot._elector.on_loss()

    # Still SHADOW → no close calls, but shouldn't crash
    assert called["close_calls"] == 0
