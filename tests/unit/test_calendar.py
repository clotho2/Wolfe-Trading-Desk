"""
Calendar Guard Tests - Proving the Fed can't surprise us
"""

import json
import pytest
from datetime import datetime, timedelta, timezone
from pathlib import Path
import tempfile

from engine.calendar import CalendarGuard, EconomicEvent, EventTier


class TestCalendarGuard:
    """Test suite for news blackout protection"""
    
    def test_primary_failover_extends_blackout(self):
        """Verify failover adds 5 minutes to all blackout windows"""
        
        # Create guard with non-existent primary (forces failover)
        guard = CalendarGuard(primary_path=Path("/nonexistent/path.json"))
        
        # Should be in failover mode
        assert guard.failover_active is True
        
        # Check that backup events exist
        assert len(guard.events) > 0
        
        # Verify extended blackout window
        event = guard.events[0]
        start, end = event.get_blackout_window(failover_active=True)
        
        # For TIER_1_STANDARD in failover: 10+5=15 minutes before/after
        if event.tier == EventTier.TIER_1_STANDARD:
            expected_duration = timedelta(minutes=30)  # 15 before + 15 after
        else:  # TIER_1_RATES
            expected_duration = timedelta(minutes=40)  # 20 before + 20 after
            
        actual_duration = end - start
        assert actual_duration == expected_duration
        
    def test_get_blackout_during_event(self):
        """Verify get_blackout returns True during event window"""
        
        # Create test data
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            test_time = datetime.now(timezone.utc)
            test_data = {
                "events": [
                    {
                        "id": "TEST_NFP",
                        "name": "Non-Farm Payrolls",
                        "currency": "USD",
                        "timestamp": test_time.isoformat(),
                        "tier": "tier1_standard"
                    }
                ]
            }
            json.dump(test_data, f)
            temp_path = Path(f.name)
            
        try:
            # Create guard with test data
            guard = CalendarGuard(primary_path=temp_path)
            
            # Test during blackout (event time)
            assert guard.get_blackout("EURUSD", test_time) is True
            
            # Test 5 minutes before event (within 10-minute window)
            assert guard.get_blackout("EURUSD", test_time - timedelta(minutes=5)) is True
            
            # Test 5 minutes after event (within 10-minute window)
            assert guard.get_blackout("EURUSD", test_time + timedelta(minutes=5)) is True
            
            # Test outside blackout (20 minutes before)
            assert guard.get_blackout("EURUSD", test_time - timedelta(minutes=20)) is False
            
            # Test outside blackout (20 minutes after)
            assert guard.get_blackout("EURUSD", test_time + timedelta(minutes=20)) is False
            
        finally:
            temp_path.unlink()
            
    def test_symbol_impact_mapping(self):
        """Verify currency impact maps to correct symbols"""
        
        guard = CalendarGuard()
        
        # USD impacts
        usd_symbols = guard.impact_for("USD")
        assert "EURUSD" in usd_symbols
        assert "GBPUSD" in usd_symbols
        assert "XAUUSD" in usd_symbols
        assert "US30" in usd_symbols
        
        # EUR impacts
        eur_symbols = guard.impact_for("EUR")
        assert "EURUSD" in eur_symbols
        assert "EURGBP" in eur_symbols
        assert "DAX40" in eur_symbols
        
        # Non-existent currency
        assert guard.impact_for("XXX") == []
        
    def test_rate_decision_longer_blackout(self):
        """Verify rate decisions get ±15 minute windows"""
        
        event = EconomicEvent(
            event_id="ECB_RATE",
            name="ECB Rate Decision",
            currency="EUR",
            timestamp=datetime.now(timezone.utc),
            tier=EventTier.TIER_1_RATES
        )
        
        # Normal window
        start, end = event.get_blackout_window(failover_active=False)
        assert (end - start) == timedelta(minutes=30)  # 15 before + 15 after
        
        # Failover window
        start, end = event.get_blackout_window(failover_active=True)
        assert (end - start) == timedelta(minutes=40)  # 20 before + 20 after
        
    def test_nfp_standard_blackout(self):
        """Verify NFP/CPI/FOMC get ±10 minute windows"""
        
        event = EconomicEvent(
            event_id="NFP",
            name="Non-Farm Payrolls",
            currency="USD",
            timestamp=datetime.now(timezone.utc),
            tier=EventTier.TIER_1_STANDARD
        )
        
        # Normal window
        start, end = event.get_blackout_window(failover_active=False)
        assert (end - start) == timedelta(minutes=20)  # 10 before + 10 after
        
        # Failover window
        start, end = event.get_blackout_window(failover_active=True)
        assert (end - start) == timedelta(minutes=30)  # 15 before + 15 after