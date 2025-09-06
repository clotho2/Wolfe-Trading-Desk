# path: shared/events/bus_testutils.py
from __future__ import annotations

from dataclasses import asdict
from typing import Any, Callable, Iterable, List, Optional

from shared.events.bus import Event, bus

Predicate = Callable[[Event], bool]


def drain() -> List[Event]:
    """Drain and return all queued events (test helper)."""
    return bus.drain()


def find(reason: str) -> List[Event]:
    """Drain and return only events with matching reason."""
    return [e for e in bus.drain() if e.reason == reason]


def assert_reason_once(
    reason: str,
    *,
    where: Optional[Predicate] = None,
    contains: Optional[dict[str, Any]] = None,
) -> Event:
    """Assert exactly one matching event was emitted.

    Args:
        reason: Event "reason" string to match.
        where: Optional predicate(Event) -> bool for advanced matching.
        contains: Optional subset of payload key/values that must match.

    Returns:
        The single matching Event.

    Raises:
        AssertionError if zero or multiple matches are found.
    """
    events = bus.drain()
    matches: List[Event] = []

    def _ok(e: Event) -> bool:
        if e.reason != reason:
            return False
        if contains:
            for k, v in contains.items():
                if e.payload.get(k) != v:
                    return False
        if where and not where(e):
            return False
        return True

    for e in events:
        if _ok(e):
            matches.append(e)

    if len(matches) != 1:
        debug = {
            "requested_reason": reason,
            "contains": contains,
            "total_events": len(events),
            "observed_reasons": [e.reason for e in events],
        }
        raise AssertionError(f"Expected exactly one '{reason}' event, got {len(matches)} — {debug}")

    return matches[0]
