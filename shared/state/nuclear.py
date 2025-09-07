# path: shared/state/nuclear.py
"""Nuclear state management for emergency lockdown controls."""

from __future__ import annotations

from typing import Optional

# Global state variables
_active: bool = False
_last_nonce: Optional[str] = None


def is_active() -> bool:
    """Check if nuclear lockdown is currently active."""
    return _active


def engage() -> None:
    """Activate nuclear lockdown state."""
    global _active
    _active = True


def clear() -> None:
    """Clear nuclear lockdown state."""
    global _active
    _active = False


def set_last_nonce(nonce: str) -> None:
    """Set the last used nonce for nuclear operations."""
    global _last_nonce
    _last_nonce = nonce


def last_nonce_used() -> Optional[str]:
    """Get the last used nonce for nuclear operations."""
    return _last_nonce