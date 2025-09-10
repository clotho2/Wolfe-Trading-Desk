# path: core/executor/register.py
from __future__ import annotations
from typing import Any, Dict, Optional

_REGISTRY: Dict[str, Any] = {}
_STRATEGY_REGISTRY: Dict[str, Any] = {}


def register_adapter(name: str, adapter: Any) -> None:
    _REGISTRY.setdefault(name, adapter)


def get_adapter(name: str) -> Optional[Any]:
    return _REGISTRY.get(name)


def register_strategy(name: str, strategy_class: Any) -> None:
    """Register a strategy class for instantiation."""
    _STRATEGY_REGISTRY[name] = strategy_class


def get_strategy_class(name: str) -> Optional[Any]:
    """Get a registered strategy class."""
    return _STRATEGY_REGISTRY.get(name)


def list_strategies() -> Dict[str, Any]:
    """List all registered strategies."""
    return _STRATEGY_REGISTRY.copy()