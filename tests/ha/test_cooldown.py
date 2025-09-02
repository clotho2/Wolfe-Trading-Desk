# (Handled in LeaderElector._maybe_auto_flat_all from Commit 16) + additional test
# path: tests/ha/test_cooldown.py
import pytest

from config.settings import settings
from infra.ha.leader import LeaderElector


@pytest.mark.asyncio
async def test_cooldown_prevents_duplicate_flat_all(monkeypatch):
    import fakeredis.aioredis as fakeredis

    calls = {"n": 0}

    class A:
        async def flat_all(self, reason: str):
            calls["n"] += 1
            return []

    from core.executor.registry import register_adapter

    register_adapter("mt5", A())
    r = fakeredis.FakeRedis()
    el = LeaderElector(r, settings.HA_LOCK_KEY, settings.LOCK_TTL_MS, settings.HEARTBEAT_MS)
    monkeypatch.setattr(settings, "FEATURES_AUTO_FLAT_ALL_ON_LOCK_LOSS", True, raising=False)
    await el.force_loss_for_test()
    await el.force_loss_for_test()
    assert calls["n"] == 1
