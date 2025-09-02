# path: infra/ha/leader.py
from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass
from typing import Awaitable, Callable, Optional

from redis.asyncio import Redis

from config.settings import settings
from infra.ha.ack import has_ack
from ops.audit.immutable_audit import append_event
from shared.services.registry import get_adapter
from shared.state.runtime import LockdownState, get_lockdown, set_lockdown


OnGain = Callable[[int], Awaitable[None]]
OnLoss = Callable[[], Awaitable[None]]


@dataclass
class LeaderConfig:
    lock_key: str
    ttl_ms: int
    heartbeat_ms: int


class LeaderElector:
    """Redis-based leader election with fencing tokens and split-brain handling."""

    def __init__(self, redis: Redis, lock_key: str, ttl_ms: int, heartbeat_ms: int, *, fencing: bool = True) -> None:
        self.redis = redis
        self.ttl_ms = int(ttl_ms)
        self.heartbeat_ms = int(heartbeat_ms)
        self.lock_key = lock_key
        self.fencing = fencing

        self.is_leader: bool = False
        self.token: Optional[int] = None
        self.last_hb_ts: Optional[float] = None
        self._task: Optional[asyncio.Task] = None

        # External hooks
        self.on_gain: Optional[OnGain] = None
        self.on_loss: Optional[OnLoss] = None

        # Internal cooldown to avoid flapping mass-close
        self._last_flat_ms: Optional[float] = None
        self._cooldown_ms = 5000
        self._stopped = False
        self._blocked_for_ack = False

    async def start(self) -> None:
        if self._task:
            return
        self._stopped = False
        self._task = asyncio.create_task(self._run())

    async def stop(self) -> None:
        self._stopped = True
        if self._task:
            self._task.cancel()
            with contextlib.suppress(Exception):
                await self._task
            self._task = None

    async def _run(self) -> None:
        try:
            while not self._stopped:
                if not self.is_leader:
                    # If previously lost, require human ack before re-acquire
                    if self._blocked_for_ack and not await has_ack(self.redis):
                        await asyncio.sleep(self.heartbeat_ms / 1000)
                        continue
                    await self._attempt_acquire()
                else:
                    ok = await self._heartbeat()
                    if not ok:
                        await self._handle_loss()
                await asyncio.sleep(self.heartbeat_ms / 1000)
        except asyncio.CancelledError:
            return

    async def _attempt_acquire(self) -> None:
        # Fencing token via INCR
        token = int(await self.redis.incr("ha:fencing_seq")) if self.fencing else int(time.time() * 1000)
        # SET key NX PX ttl with token value
        set_ok = await self.redis.set(self.lock_key, str(token), nx=True, px=self.ttl_ms)
        if not set_ok:
            return
        self.is_leader = True
        self.token = token
        self.last_hb_ts = time.time()
        if self.on_gain:
            await self.on_gain(token)
        append_event({"evt": "HA_LOCK_GAINED", "payload": {"token": token}})

    async def _heartbeat(self) -> bool:
        # Only leader heartbeats; if key vanished, we lost
        pexp = await self.redis.pexpire(self.lock_key, self.ttl_ms)
        if not pexp:
            return False
        self.last_hb_ts = time.time()
        return True

    async def _handle_loss(self) -> None:
        prev = self.token
        self.is_leader = False
        self.token = None
        append_event({"evt": "HA_LOCK_LOST", "payload": {"token": prev}})
        if self.on_loss:
            await self.on_loss()
        # Split-brain protection + executor hook
        await self._maybe_auto_flat_all()
        # Block re-acquire until human ack
        self._blocked_for_ack = True

    async def _maybe_auto_flat_all(self) -> None:
        if not settings.FEATURES_AUTO_FLAT_ALL_ON_LOCK_LOSS:
            return
        # Idempotent if already in lockdown
        if get_lockdown() == LockdownState.SPLIT_BRAIN:
            return
        # Cooldown guard
        now_ms = time.time() * 1000
        if self._last_flat_ms and (now_ms - self._last_flat_ms) < self._cooldown_ms:
            return
        self._last_flat_ms = now_ms

        set_lockdown(LockdownState.SPLIT_BRAIN)
        adapter = get_adapter("mt5") or get_adapter(None)
        results = []
        if adapter is not None:
            results = await adapter.flat_all("split_brain")
        append_event({"evt": "FLAT_ALL_EXECUTED", "payload": {"mode": getattr(settings.EXECUTOR_MODE, 'value', str(settings.EXECUTOR_MODE)), "count": len(results)}})

    # Test helpers
    async def force_loss_for_test(self) -> None:
        await self._handle_loss()

    async def attempt_reacquire_for_test(self) -> None:
        self._blocked_for_ack = False
        await self._attempt_acquire()
