# path: tests/ha/test_leader_redis.py
import asyncio

import pytest
from fastapi.testclient import TestClient

from config.settings import settings
from infra.ha.leader import LeaderElector
from infra.ha.ack import get_ack
from ops.dashboard.app import app


@pytest.mark.asyncio
async def test_fencing_monotonic(monkeypatch):
    import fakeredis.aioredis as fakeredis

    r = fakeredis.FakeRedis()
    el = LeaderElector(r, settings.HA_LOCK_KEY, settings.LOCK_TTL_MS, settings.HEARTBEAT_MS)
    await el._attempt_acquire()
    t1 = el.token
    # Force loss, then ack to allow reacquire
    await el.force_loss_for_test()
    await r.hset("ha:ack", "split_brain_ack", "x")
    await el.attempt_reacquire_for_test()
    t2 = el.token
    assert t1 and t2 and t2 > t1


@pytest.mark.asyncio
async def test_loss_triggers_flat_all_once(monkeypatch):
    import fakeredis.aioredis as fakeredis

    calls = {"flat": 0}

    class DummyAdapter:
        async def list_open_positions(self):
            return []
        async def flat_all(self, reason: str):
            calls["flat"] += 1
            return []

    from core.executor.registry import register_adapter
    register_adapter("mt5", DummyAdapter())

    r = fakeredis.FakeRedis()
    el = LeaderElector(r, settings.HA_LOCK_KEY, settings.LOCK_TTL_MS, settings.HEARTBEAT_MS)
    # Enable feature
    monkeypatch.setattr(settings, "FEATURES_AUTO_FLAT_ALL_ON_LOCK_LOSS", True, raising=False)

    await el.force_loss_for_test()
    await el.force_loss_for_test()  # within cooldown
    assert calls["flat"] == 1


@pytest.mark.asyncio
async def test_ack_allows_reacquire(monkeypatch):
    import fakeredis.aioredis as fakeredis

    r = fakeredis.FakeRedis()
    el = LeaderElector(r, settings.HA_LOCK_KEY, settings.LOCK_TTL_MS, settings.HEARTBEAT_MS)
    await el._attempt_acquire()
    await el.force_loss_for_test()

    # Try reacquire without ack → blocked
    await el._attempt_acquire()
    assert not el.is_leader

    # Now POST /ha/ack
    client = TestClient(app)
    res = client.post("/ha/ack", headers={"Authorization": f"Bearer {settings.DASH_TOKEN}"})
    assert res.status_code == 200

    # Elector allowed
    await el.attempt_reacquire_for_test()
    assert el.is_leader
