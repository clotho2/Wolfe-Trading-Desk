# path: core/executor/mode.py
from __future__ import annotations

from enum import Enum


class Mode(str, Enum):
    LIVE = "LIVE"
    DRY_RUN = "DRY_RUN"
    SHADOW = "SHADOW"


def normalize(value: str) -> Mode:
    v = (value or "").upper()
    if v in {"HONEYPOT", "PAPER"}:
        return Mode.SHADOW
    return Mode[v]
