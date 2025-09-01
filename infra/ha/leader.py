# path: infra/ha/leader.py
from __future__ import annotations

import asyncio
import time
from typing import Awaitable, Callable, Optional

from redis.asyncio import Redis


class LeaderElector:
    """Redis leader election with fencing and callbacks.

    - Acquire via SET NX PX ttl with value "token:<int>"; tokens from INCR(lock_key+":token").
    - Heartbeat verifies current value before pexpire.
    - Calls `on_gain(token)` and `on_loss()` when lock changes.
    - Idempotent `start()`; use app-lifetime task.
    """

    def __init__(
        self,
        redis: Redis,
        lock_key: str,
        ttl_ms: int,
        heartbeat_ms: int,
        fencing: bool = True,
    ) -> None:
        self.redis = redis
        self.lock_key = lock_key
        self.token_key = f"{lock_key}:token"
        self.ttl_ms = int(ttl_ms)
        self.heartbeat_ms = int(heartbeat_ms)
        self.fencing = fencing

        self.on_gain: Optional[Callable[[int], Awaitable[None]]] = None
        self.on_loss: Optional[Callable[[], Awaitable[None]]] = None

        self._leader = False
        self._token: Optional[int] = None
        self._value: Optional[bytes] = None
        self._task: Optional[asyncio.Task] = None
        self._running = False
        self._last_hb: Optional[float] = None

    # -------- Public props --------
    @property
    def is_leader(self) -> bool:
        return self._leader

    @property
    def token(self) -> Optional[int]:
        return self._token

    # -------- Lifecycle --------
    async def start(self) -> None:
        if self._running:
            return
        self._running = True
        self._task = asyncio.create_task(self._loop(), name="ha-elector")

    async def _loop(self) -> None:
        while self._running:
            try:
                if not self._leader:
                    await self._try_acquire()
                else:
                    await self._heartbeat()
            except Exception:
                # swallow to keep loop alive; observability is via audit bus in bootstrap
                pass
            await asyncio.sleep(self.heartbeat_ms / 1000.0)

    # -------- Internals --------
    async def _try_acquire(self) -> None:
        token = int(await self.redis.incr(self.token_key)) if self.fencing else 1
        value = f"token:{token}".encode()
        ok = await self.redis.set(self.lock_key, value, nx=True, px=self.ttl_ms)
        if ok:
            self._leader = True
            self._token = token
            self._value = value
            self._last_hb = time.time()
            if self.on_gain:
                await self.on_gain(token)

    async def _heartbeat(self) -> None:
        current = await self.redis.get(self.lock_key)
        if current != self._value:
            await self._lost()
            return
        await self.redis.pexpire(self.lock_key, self.ttl_ms)
        self._last_hb = time.time()

    async def _lost(self) -> None:
        self._leader = False
        token = self._token
        self._token = None
        self._value = None
        if self.on_loss:
            await self.on_loss()
