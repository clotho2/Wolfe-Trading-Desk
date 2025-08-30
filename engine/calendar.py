"""
Calendar Guard with Failover - v0.4.3
Because the Fed ruins everything, and when primary feeds die, we don't.
"""

import json
import logging
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Set, Tuple
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

logger = logging.getLogger(__name__)


class EventTier(Enum):
    """Event impact tiers - because not all news is created equal"""
    TIER_1_STANDARD = "tier1_standard"  # NFP, CPI, FOMC
    TIER_1_RATES = "tier1_rates"        # Central bank rate decisions
    TIER_2 = "tier2"                     # Lesser events
    

@dataclass
class EconomicEvent:
    """An event that can fuck up your trades"""
    event_id: str
    name: str
    currency: str
    timestamp: datetime
    tier: EventTier
    
    def get_blackout_window(self, failover_active: bool = False) -> Tuple[datetime, datetime]:
        """Calculate blackout window for this event"""
        
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
    """
    The guardian against news-induced account destruction.
    When central banks speak, we shut the fuck up and wait.
    """
    
    # Symbol impact mapping - which symbols die when a currency has news
    IMPACT_MAP = {
        "USD": ["EURUSD", "GBPUSD", "USDJPY", "USDCHF", "USDCAD", "AUDUSD", "NZDUSD", 
                "XAUUSD", "XAGUSD", "US30", "NAS100", "SPX500"],
        "EUR": ["EURUSD", "EURGBP", "EURJPY", "EURCHF", "EURAUD", "EURNZD", "EURCAD", "DAX40"],
        "GBP": ["GBPUSD", "EURGBP", "GBPJPY", "GBPCHF", "GBPAUD", "GBPNZD", "GBPCAD", "UK100"],
        "JPY": ["USDJPY", "EURJPY", "GBPJPY", "AUDJPY", "NZDJPY", "CADJPY", "CHFJPY", "NKY225"],
        "CHF": ["USDCHF", "EURCHF", "GBPCHF", "AUDCHF", "NZDCHF", "CADCHF", "CHFJPY"],
        "CAD": ["USDCAD", "EURCAD", "GBPCAD", "AUDCAD", "NZDCAD", "CADCHF", "CADJPY", "WTIUSD"],
        "AUD": ["AUDUSD", "EURAUD", "GBPAUD", "AUDJPY", "AUDCHF", "AUDCAD", "AUDNZD", "AUS200"],
        "NZD": ["NZDUSD", "EURNZD", "GBPNZD", "NZDJPY", "NZDCHF", "NZDCAD", "AUDNZD"],
    }
    
    def __init__(self, primary_path: Optional[Path] = None):
        """Initialize with optional primary data source"""
        self.primary_path = primary_path or Path("data/events.json")
        self.events: List[EconomicEvent] = []
        self.failover_active: bool = False
        
        # Load events
        self._load_events()
        
    def _load_events(self) -> None:
        """Load events from primary or fallback to secondary"""
        
        try:
            # Try primary provider
            if self.primary_path and self.primary_path.exists():
                with open(self.primary_path, 'r') as f:
                    data = json.load(f)
                    
                self.events = []
                for event_data in data.get('events', []):
                    event = EconomicEvent(
                        event_id=event_data['id'],
                        name=event_data['name'],
                        currency=event_data['currency'],
                        timestamp=datetime.fromisoformat(event_data['timestamp']),
                        tier=EventTier(event_data['tier'])
                    )
                    self.events.append(event)
                    
                self.failover_active = False
                logger.info(f"Loaded {len(self.events)} events from primary provider")
                
            else:
                # Primary failed, use secondary
                self._load_secondary()
                
        except Exception as e:
            logger.warning(f"Primary provider failed: {e}")
            self._load_secondary()
            
    def _load_secondary(self) -> None:
        """Fallback to hardcoded secondary provider"""
        
        logger.warning("Using secondary provider - extending all blackouts by 5 minutes")
        self.failover_active = True
        
        # Hardcoded backup events
        now = datetime.now(timezone.utc)
        
        self.events = [
            EconomicEvent(
                event_id="NFP_BACKUP",
                name="Non-Farm Payrolls",
                currency="USD",
                timestamp=now.replace(hour=13, minute=30, second=0, microsecond=0),
                tier=EventTier.TIER_1_STANDARD
            ),
            EconomicEvent(
                event_id="ECB_BACKUP",
                name="ECB Rate Decision",
                currency="EUR",
                timestamp=now.replace(hour=12, minute=45, second=0, microsecond=0),
                tier=EventTier.TIER_1_RATES
            ),
        ]
        
    def get_blackout(self, symbol: str, now_utc: datetime) -> bool:
        """
        Check if a symbol is in blackout at the given time.
        This is where we protect capital from news volatility.
        """
        
        # Find all currencies that impact this symbol
        impacted_currencies = set()
        for currency, symbols in self.IMPACT_MAP.items():
            if symbol in symbols:
                impacted_currencies.add(currency)
                
        if not impacted_currencies:
            return False  # Symbol not in our impact map
            
        # Check if any relevant event creates a blackout
        for event in self.events:
            if event.currency not in impacted_currencies:
                continue
                
            start, end = event.get_blackout_window(self.failover_active)
            
            if start <= now_utc <= end:
                logger.info(
                    f"BLACKOUT: {symbol} blocked due to {event.name} "
                    f"({event.currency}) at {event.timestamp}"
                )
                return True
                
        return False
        
    def impact_for(self, currency: str) -> List[str]:
        """
        Get all symbols impacted by news for a given currency.
        When the Fed speaks, everything USD gets frozen.
        """
        return self.IMPACT_MAP.get(currency, [])
        
    def get_active_blackouts(self, now_utc: datetime) -> Dict[str, List[str]]:
        """Get all currently active blackouts and affected symbols"""
        
        active = {}
        
        for event in self.events:
            start, end = event.get_blackout_window(self.failover_active)
            
            if start <= now_utc <= end:
                affected_symbols = self.impact_for(event.currency)
                active[f"{event.name} ({event.currency})"] = affected_symbols
                
        return active