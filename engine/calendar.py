# engine/calendar.py
"""Calendar Guard with failover — v0.4.3.
Determines symbol blackout windows around major economic events.
"""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


class EventTier(Enum):
    """Event impact tiers."""

    TIER_1_STANDARD = "tier1_standard"  # NFP, CPI, FOMC
    TIER_1_RATES = "tier1_rates"  # Central bank rate decisions
    TIER_2 = "tier2"  # Lesser events


@dataclass
class EconomicEvent:
    """Represents a scheduled economic event and its blackout policy."""

    event_id: str
    name: str
    currency: str
    timestamp: datetime
    tier: EventTier

    def get_blackout_window(self, failover_active: bool = False) -> Tuple[datetime, datetime]:
        """Calculate inclusive blackout window around the event timestamp."""

        # Base windows by tier
        if self.tier == EventTier.TIER_1_RATES:
            before_minutes = 15
            after_minutes = 15
        elif self.tier == EventTier.TIER_1_STANDARD:
            before_minutes = 10
            after_minutes = 10
        else:
            before_minutes = 5
            after_minutes = 5

        # Extend by 5 minutes if failover active
        if failover_active:
            before_minutes += 5
            after_minutes += 5

        start = self.timestamp - timedelta(minutes=before_minutes)
        end = self.timestamp + timedelta(minutes=after_minutes)
        return start, end


class CalendarGuard:
    """News blackout guard.

    Loads events from a primary JSON feed (file path) and transparently
    fails over to a conservative secondary provider when necessary.
    """

    # Symbol impact mapping — which symbols are affected when a currency
    # has a TIER_1 event.
    IMPACT_MAP = {
        "USD": [
            "EURUSD",
            "GBPUSD",
            "USDJPY",
            "USDCHF",
            "USDCAD",
            "AUDUSD",
            "NZDUSD",
            "XAUUSD",
            "XAGUSD",
            "US30",
            "NAS100",
            "SPX500",
        ],
        "EUR": [
            "EURUSD",
            "EURGBP",
            "EURJPY",
            "EURCHF",
            "EURAUD",
            "EURNZD",
            "EURCAD",
            "DAX40",
        ],
        "GBP": [
            "GBPUSD",
            "EURGBP",
            "GBPJPY",
            "GBPCHF",
            "GBPAUD",
            "GBPNZD",
            "GBPCAD",
            "UK100",
        ],
        "JPY": [
            "USDJPY",
            "EURJPY",
            "GBPJPY",
            "AUDJPY",
            "NZDJPY",
            "CADJPY",
            "CHFJPY",
            "NKY225",
        ],
        "CHF": [
            "USDCHF",
            "EURCHF",
            "GBPCHF",
            "AUDCHF",
            "NZDCHF",
            "CADCHF",
            "CHFJPY",
        ],
        "CAD": [
            "USDCAD",
            "EURCAD",
            "GBPCAD",
            "AUDCAD",
            "NZDCAD",
            "CADCHF",
            "CADJPY",
            "WTIUSD",
        ],
        "AUD": [
            "AUDUSD",
            "EURAUD",
            "GBPAUD",
            "AUDJPY",
            "AUDCHF",
            "AUDCAD",
            "AUDNZD",
            "AUS200",
        ],
        "NZD": [
            "NZDUSD",
            "EURNZD",
            "GBPNZD",
            "NZDJPY",
            "NZDCHF",
            "NZDCAD",
            "AUDNZD",
        ],
    }

    def __init__(self, primary_path: Optional[Path] = None):
        self.primary_path = primary_path or Path("data/events.json")
        self.events: List[EconomicEvent] = []
        self.failover_active: bool = False
        self._load_events()

    def _load_events(self) -> None:
        """Load events from primary feed or fallback to secondary."""
        try:
            if self.primary_path and self.primary_path.exists():
                with open(self.primary_path, "r") as f:
                    data = json.load(f)
                self.events = []
                for event_data in data.get("events", []):
                    event = EconomicEvent(
                        event_id=event_data["id"],
                        name=event_data["name"],
                        currency=event_data["currency"],
                        timestamp=datetime.fromisoformat(event_data["timestamp"]),
                        tier=EventTier(event_data["tier"]),
                    )
                    self.events.append(event)
                self.failover_active = False
                logger.info("Loaded %d events from primary provider", len(self.events))
            else:
                self._load_secondary()
        except Exception as e:  # pragma: no cover (defensive)
            logger.warning("Primary provider failed: %s", e)
            self._load_secondary()

    def _load_secondary(self) -> None:
        """Fallback to a conservative secondary event set."""
        logger.warning("Using secondary provider — extending all blackouts by 5 minutes")
        self.failover_active = True
        now = datetime.now(timezone.utc)
        self.events = [
            EconomicEvent(
                event_id="NFP_BACKUP",
                name="Non-Farm Payrolls",
                currency="USD",
                timestamp=now.replace(hour=13, minute=30, second=0, microsecond=0),
                tier=EventTier.TIER_1_STANDARD,
            ),
            EconomicEvent(
                event_id="ECB_BACKUP",
                name="ECB Rate Decision",
                currency="EUR",
                timestamp=now.replace(hour=12, minute=45, second=0, microsecond=0),
                tier=EventTier.TIER_1_RATES,
            ),
        ]

    def get_blackout(self, symbol: str, now_utc: datetime) -> bool:
        """Return True if *symbol* is in blackout at *now_utc*."""
        impacted_currencies: set[str] = set()
        for currency, symbols in self.IMPACT_MAP.items():
            if symbol in symbols:
                impacted_currencies.add(currency)
        if not impacted_currencies:
            return False

        for event in self.events:
            if event.currency not in impacted_currencies:
                continue
            start, end = event.get_blackout_window(self.failover_active)
            if start <= now_utc <= end:
                logger.info(
                    "BLACKOUT: %s blocked due to %s (%s) at %s",
                    symbol,
                    event.name,
                    event.currency,
                    event.timestamp,
                )
                return True
        return False

    def impact_for(self, currency: str) -> List[str]:
        """Return all symbols impacted by the given *currency*."""
        return self.IMPACT_MAP.get(currency, [])

    def get_active_blackouts(self, now_utc: datetime) -> Dict[str, List[str]]:
        """Return mapping of active event → affected symbols at *now_utc*."""
        active: Dict[str, List[str]] = {}
        for event in self.events:
            start, end = event.get_blackout_window(self.failover_active)
            if start <= now_utc <= end:
                affected_symbols = self.impact_for(event.currency)
                active[f"{event.name} ({event.currency})"] = affected_symbols
        return active
