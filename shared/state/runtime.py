# path: shared/state/runtime.py
from __future__ import annotations

from enum import Enum
from typing import Optional


class LockdownState(str, Enum):
    NONE = "NONE"
    SPLIT_BRAIN = "SPLIT_BRAIN"


_state: LockdownState = LockdownState.NONE


def get_lockdown() -> LockdownState:
    return _state


def set_lockdown(new_state: LockdownState) -> None:
    global _state
    _state = new_state
