# path: shared/services/registry.py
from __future__ import annotations
from typing import Any, Optional

_adapter: Optional[Any] = None


def register_adapter(adapter: Any) -> None:
    global _adapter
    _adapter = adapter


def get_adapter() -> Optional[Any]:
    return _adapter
