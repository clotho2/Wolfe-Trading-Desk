# path: shared/utils/backoff.py
from __future__ import annotations

import random
from typing import Iterable, List


def plan_retries(base_ms: int, max_ms: int, jitter_ms: int, retries: int, *, seed: int | None = None) -> List[int]:
    """Return retry delays with deterministic jitter for tests.

    backoff: t(i) = min(max_ms, base_ms * 2**i) ± jitter
    """
    rng = random.Random(seed)
    out: List[int] = []
    for i in range(retries):
        core = min(max_ms, base_ms * (2 ** i))
        j = rng.randint(-jitter_ms, jitter_ms)
        out.append(max(0, core + j))
    return out
