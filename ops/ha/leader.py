# path: ops/ha/leader.py
from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass
from typing import Callable, Optional

from redis.asyncio import Redis

from config.settings import settings
from ops.audit.immutable_audit import append_event


@dataclass
class LeaderStatus:
    is_leader: bool
    fencing_token: Optional[int]
    lockdown_active: bool
    last_heartbeat_ts: float | None


class RedisLeaderElector:
    """Redis-based leader election with fencing tokens and split-brain lockdown.

    Behavior (v0.4.3):
    - Acquire via SET NX PX ttl using value "{node_id}:{token}" where token = INCR(token_key).
    - Heartbeat every HEARTBEAT_MS if we still own the lock (value matches); else trigger FLAT_ALL and lockdown.
    - After lock loss: set local lockdown until human ack; do not trade until leadership re-proven and acked.
    """

    def __init__(
        self,
        redis: Redis,
        node_id: str,
        lock_key: str = "wolfe:ha:lock",
        token_key: str = "wolfe:ha:token",
        ttl_ms: int = settings.LOCK_TTL_MS,
        heartbeat_ms: int = settings.HEARTBEAT_MS,
        on_flat_all: Optional[Callable[[], None]] = None,
    ) -> None:
        self.redis = redis
        self.node_id = node_id
        self.lock_key = lock_key
        self.token_key = token_key
        self.ttl_ms = int(ttl_ms)
        self.heartbeat_ms = int(heartbeat_ms)
        self.on_flat_all = on_flat_all

        self._running = False
        self._task: Optional[asyncio.Task] = None
        self._token: Optional[int] = None
        self._lock_value: Optional[bytes] = None
        self._last_hb: Optional[float] = None
        self._lockdown = False
        self._human_ack = False

    # ------------------------------- lifecycle -------------------------------
    async def start(self) -> None:
        if self._running:
            return
        self._running = True
        self._task = asyncio.create_task(self._run(), name="ha-leader")

    async def stop(self) -> None:
        self._running = False
        if self._task:
            await asyncio.wait([self._task])
            self._task = None

    # -------------------------------- status ---------------------------------
    def status(self) -> LeaderStatus:
        return LeaderStatus(
            is_leader=self._is_leader(),
            fencing_token=self._token,
            lockdown_active=self._lockdown,
            last_heartbeat_ts=self._last_hb,
        )

    def _is_leader(self) -> bool:
        return self._lock_value is not None and self._token is not None

    # --------------------------------- ack -----------------------------------
    def human_ack(self) -> None:
        """Clear lockdown after human acknowledgement."""
        self._human_ack = True
        self._lockdown = False

    # ------------------------------- internals -------------------------------
    async def _run(self) -> None:
        while self._running:
            try:
                if not self._is_leader():
                    await self._try_acquire()
                else:
                    await self._heartbeat()
            except Exception as e:  # defensive
                append_event({"evt": "HA_LOOP_ERROR", "payload": {"error": repr(e)}})
            await asyncio.sleep(self.heartbeat_ms / 1000.0)

    async def _try_acquire(self) -> None:
        if self._lockdown and not self._human_ack:
            return  # wait for human ack

        token = int(await self.redis.incr(self.token_key))
        value_str = f"{self.node_id}:{token}"
        ok = await self.redis.set(self.lock_key, value_str, nx=True, px=self.ttl_ms)
        if ok:
            self._token = token
            self._lock_value = value_str.encode()
            self._last_hb = time.time()
            self._human_ack = False  # consumed
            append_event({"evt": "HA_LEADER_ACQUIRED", "payload": {"token": token, "node": self.node_id}})
        else:
            # not acquired; keep trying on next loop
            pass

    async def _heartbeat(self) -> None:
        # validate ownership
        current = await self.redis.get(self.lock_key)
        if current != self._lock_value:
            await self._on_lock_lost()
            return
        # extend TTL
        await self.redis.pexpire(self.lock_key, self.ttl_ms)
        self._last_hb = time.time()

    async def _on_lock_lost(self) -> None:
        # transition to follower + lockdown
        prev_token = self._token
        self._token = None
        self._lock_value = None
        self._lockdown = True
        append_event({
            "evt": "HA_LOCK_LOST",
            "payload": {"node": self.node_id, "token": prev_token, "action": "FLAT_ALL", "lockdown": "SPLIT_BRAIN"},
        })
        # execute FLAT_ALL as a side effect if provided
        if self.on_flat_all:
            try:
                self.on_flat_all()
            except Exception as e:
                append_event({"evt": "HA_FLAT_ALL_ERROR", "payload": {"error": repr(e)}})


# --------- simple registry for dashboard/API integration (optional) ---------
_LEADER: Optional[RedisLeaderElector] = None


def set_leader(elector: RedisLeaderElector) -> None:
    global _LEADER
    _LEADER = elector


def get_leader() -> Optional[RedisLeaderElector]:
    return _LEADER
