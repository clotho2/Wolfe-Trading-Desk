# path: core/executor/registry.py
from __future__ import annotations
from typing import Any, Dict, Optional

_REGISTRY: Dict[str, Any] = {}


def register_adapter(name: str, adapter: Any) -> None:
    _REGISTRY.setdefault(name, adapter)


def get_adapter(name: str) -> Optional[Any]:
    return _REGISTRY.get(name)
