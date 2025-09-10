# path: tests/strategies/test_pilot_sma.py
from __future__ import annotations

import pytest
from datetime import datetime, timezone
from unittest.mock import Mock, MagicMock, patch
from typing import List, Dict, Any

from strategies.pilot_sma import PilotSMAStrategy, Tick
from adapters.base import Order, ExecReport
from config.settings import Settings


class TestPilotSMAStrategy:
    """Test suite for PilotSMAStrategy."""
    
    @pytest.fixture
    def mock_settings(self):
        """Create mock settings with pilot_sma configuration."""
        settings = Mock(spec=Settings)
        settings.features = Mock()
        settings.features.strategy_pilot = True
        settings.strategies = Mock()
        settings.strategies.pilot_sma = {
            "symbol": "EURUSD",
            "size": 0.01,
            "fast": 20,
            "slow": 50
        }
        settings.strategies.enabled = ["pilot_sma"]
        
        # Add ComplianceGuard settings
        settings.DAILY_HARD_DD_PCT = 0.05
        settings.DAILY_SOFT_FREEZE_PCT = 0.03
        settings.FEATURES_GAP_GUARD = True
        settings.GAP_ALERT_PCT = 0.15
        settings.CORR_WINDOW_DAYS = 20
        settings.CORR_BLOCK_THRESHOLD = 0.70
        
        return settings
    
    @pytest.fixture
    def mock_adapter(self):
        """Create mock MT5 adapter."""
        adapter = Mock()
        adapter.place_order = Mock(return_value=ExecReport(status="DRY_RUN", order=None))
        return adapter
    
    @pytest.fixture
    def strategy(self, mock_settings):
        """Create strategy instance with mock settings."""
        return PilotSMAStrategy(settings=mock_settings)
    
    def generate_price_sequence_for_crossover(self, base_price: float = 1.10000) -> List[float]:
        """
        Generate a price sequence that will cause SMA crossovers.
        
        Returns a list of prices that when fed as ticks will:
        1. Build up enough history for SMA calculation (50+ prices)
        2. Create a golden cross (fast SMA crosses above slow SMA)
        3. Create a death cross (fast SMA crosses below slow SMA)
        """
        prices = []
        
        # Phase 1: Initial stable prices (50 ticks for slow SMA)
        for i in range(50):
            prices.append(base_price)
        
        # Phase 2: Create uptrend for golden cross
        # Fast SMA will react quicker to price increases
        for i in range(20):
            prices.append(base_price + 0.0001 * (i + 1))  # Rising prices
        
        # Phase 3: Strong downtrend for death cross
        # Fast SMA will react quicker to price decreases
        current_price = prices[-1]
        for i in range(25):
            prices.append(current_price - 0.0002 * (i + 1))  # Falling prices
        
        return prices
    
    def test_initialization(self, strategy):
        """Test strategy initialization with configuration."""
        assert strategy.symbol == "EURUSD"
        assert strategy.size == 0.01
        assert strategy.fast_period == 20
        assert strategy.slow_period == 50
        assert strategy.enabled is True
        assert strategy.position == 0.0
    
    def test_tick_filtering(self, strategy):
        """Test that strategy only processes ticks for configured symbol."""
        # Create tick for different symbol
        tick = Tick(
            symbol="GBPUSD",
            bid=1.25000,
            ask=1.25010,
            timestamp=datetime.now(timezone.utc)
        )
        
        # Process tick - should be ignored
        strategy.on_tick(tick)
        
        # State should remain empty
        assert len(strategy.state.prices) == 0
    
    def test_sma_calculation(self, strategy):
        """Test SMA calculation with sufficient price history."""
        base_price = 1.10000
        
        # Add exactly 50 prices
        for i in range(50):
            tick = Tick(
                symbol="EURUSD",
                bid=base_price - 0.00005,
                ask=base_price + 0.00005,
                timestamp=datetime.now(timezone.utc)
            )
            strategy.on_tick(tick)
        
        # Both SMAs should be calculated
        assert strategy.state.fast_sma is not None
        assert strategy.state.slow_sma is not None
        assert abs(strategy.state.fast_sma - base_price) < 0.0001
        assert abs(strategy.state.slow_sma - base_price) < 0.0001
    
    @patch('strategies.pilot_sma.get_adapter')
    @patch('strategies.pilot_sma.bus')
    def test_golden_cross_signal(self, mock_bus, mock_get_adapter, strategy, mock_adapter):
        """Test golden cross (upward crossover) generates BUY signal."""
        mock_get_adapter.return_value = mock_adapter
        
        prices = self.generate_price_sequence_for_crossover()
        order_placed = False
        
        # Feed prices as ticks
        for i, price in enumerate(prices):
            tick = Tick(
                symbol="EURUSD",
                bid=price - 0.00005,
                ask=price + 0.00005,
                timestamp=datetime.now(timezone.utc)
            )
            strategy.on_tick(tick)
            
            # Check if order was placed after golden cross
            if mock_adapter.place_order.called and not order_placed:
                order_placed = True
                call_args = mock_adapter.place_order.call_args[0][0]
                
                # Verify BUY order was submitted
                assert call_args.symbol == "EURUSD"
                assert call_args.side == "BUY"
                assert call_args.qty == 0.01
                
                # Verify event was emitted
                mock_bus.emit.assert_called()
                emit_call = mock_bus.emit.call_args
                assert emit_call[0][0] == "STRATEGY_SIGNAL"
                assert emit_call[1]["strategy"] == "pilot_sma"
                assert emit_call[1]["side"] == "BUY"
                
                break
        
        assert order_placed, "Golden cross should have triggered a BUY order"
    
    @patch('strategies.pilot_sma.get_adapter')
    @patch('strategies.pilot_sma.bus')
    def test_death_cross_signal(self, mock_bus, mock_get_adapter, strategy, mock_adapter):
        """Test death cross (downward crossover) generates SELL signal."""
        mock_get_adapter.return_value = mock_adapter
        
        prices = self.generate_price_sequence_for_crossover()
        buy_triggered = False
        sell_triggered = False
        
        # Feed prices as ticks
        for i, price in enumerate(prices):
            tick = Tick(
                symbol="EURUSD",
                bid=price - 0.00005,
                ask=price + 0.00005,
                timestamp=datetime.now(timezone.utc)
            )
            strategy.on_tick(tick)
            
            # Track order calls
            if mock_adapter.place_order.called:
                last_call = mock_adapter.place_order.call_args[0][0]
                
                if last_call.side == "BUY" and not buy_triggered:
                    buy_triggered = True
                elif last_call.side == "SELL" and not sell_triggered:
                    sell_triggered = True
                    
                    # Verify SELL order details
                    assert last_call.symbol == "EURUSD"
                    assert last_call.qty == 0.01
                    
                    # Verify event was emitted
                    emit_calls = mock_bus.emit.call_args_list
                    sell_event = [c for c in emit_calls if c[0][0] == "STRATEGY_SIGNAL" and c[1].get("side") == "SELL"]
                    assert len(sell_event) > 0
                    assert sell_event[0][1]["strategy"] == "pilot_sma"
                    
                    break
        
        assert buy_triggered, "Golden cross should have triggered first"
        assert sell_triggered, "Death cross should have triggered after golden cross"
    
    @patch('strategies.pilot_sma.get_adapter')
    def test_compliance_guard_blocking(self, mock_get_adapter, strategy, mock_adapter):
        """Test that ComplianceGuard blocks trading when disabled."""
        mock_get_adapter.return_value = mock_adapter
        
        # Disable ComplianceGuard
        strategy.compliance_guard.disabled = True
        
        # Generate prices that would trigger a signal
        prices = self.generate_price_sequence_for_crossover()
        
        # Feed prices
        for price in prices[:70]:  # Feed enough for golden cross
            tick = Tick(
                symbol="EURUSD",
                bid=price - 0.00005,
                ask=price + 0.00005,
                timestamp=datetime.now(timezone.utc)
            )
            strategy.on_tick(tick)
        
        # No order should be placed when ComplianceGuard is disabled
        mock_adapter.place_order.assert_not_called()
    
    @patch('strategies.pilot_sma.get_adapter')
    def test_gap_halt_blocking(self, mock_get_adapter, strategy, mock_adapter):
        """Test that gap halt blocks trading."""
        mock_get_adapter.return_value = mock_adapter
        
        # Set gap halt
        strategy.compliance_guard._gap_halted = True
        
        # Generate prices that would trigger a signal
        prices = self.generate_price_sequence_for_crossover()
        
        # Feed prices
        for price in prices[:70]:  # Feed enough for golden cross
            tick = Tick(
                symbol="EURUSD",
                bid=price - 0.00005,
                ask=price + 0.00005,
                timestamp=datetime.now(timezone.utc)
            )
            strategy.on_tick(tick)
        
        # No order should be placed during gap halt
        mock_adapter.place_order.assert_not_called()
    
    def test_position_tracking(self, strategy):
        """Test that position is tracked correctly."""
        with patch('strategies.pilot_sma.get_adapter') as mock_get_adapter:
            mock_adapter = Mock()
            mock_adapter.place_order = Mock(return_value=ExecReport(status="DRY_RUN", order=None))
            mock_get_adapter.return_value = mock_adapter
            
            # Simulate BUY signal
            strategy._handle_signal("BUY", Tick("EURUSD", 1.10000, 1.10010, datetime.now(timezone.utc)))
            assert strategy.position == 0.01
            
            # Simulate another BUY
            strategy._handle_signal("BUY", Tick("EURUSD", 1.10000, 1.10010, datetime.now(timezone.utc)))
            assert strategy.position == 0.02
            
            # Simulate SELL
            strategy._handle_signal("SELL", Tick("EURUSD", 1.10000, 1.10010, datetime.now(timezone.utc)))
            assert strategy.position == 0.01
    
    def test_get_status(self, strategy):
        """Test status reporting."""
        # Add some price data
        for i in range(50):
            tick = Tick(
                symbol="EURUSD",
                bid=1.10000,
                ask=1.10010,
                timestamp=datetime.now(timezone.utc)
            )
            strategy.on_tick(tick)
        
        status = strategy.get_status()
        
        assert status["strategy"] == "pilot_sma"
        assert status["enabled"] is True
        assert status["symbol"] == "EURUSD"
        assert status["position"] == 0.0
        assert status["price_buffer_size"] == 50
        assert status["fast_sma"] is not None
        assert status["slow_sma"] is not None
    
    def test_strategy_stop(self, strategy):
        """Test strategy can be stopped."""
        strategy.stop()
        assert strategy.enabled is False
        
        # Should not process ticks when disabled
        tick = Tick(
            symbol="EURUSD",
            bid=1.10000,
            ask=1.10010,
            timestamp=datetime.now(timezone.utc)
        )
        strategy.on_tick(tick)
        assert len(strategy.state.prices) == 0
    
    @patch('strategies.pilot_sma.get_adapter')
    def test_no_adapter_handling(self, mock_get_adapter, strategy):
        """Test graceful handling when adapter is not available."""
        mock_get_adapter.return_value = None
        
        # Should not raise exception
        strategy._handle_signal("BUY", Tick("EURUSD", 1.10000, 1.10010, datetime.now(timezone.utc)))
        
        # Position should not change
        assert strategy.position == 0.0
    
    def test_insufficient_data_no_signal(self, strategy):
        """Test that no signals are generated with insufficient data."""
        with patch('strategies.pilot_sma.get_adapter') as mock_get_adapter:
            mock_adapter = Mock()
            mock_get_adapter.return_value = mock_adapter
            
            # Add only 49 prices (less than slow period)
            for i in range(49):
                tick = Tick(
                    symbol="EURUSD",
                    bid=1.10000 + i * 0.0001,  # Rising prices
                    ask=1.10010 + i * 0.0001,
                    timestamp=datetime.now(timezone.utc)
                )
                strategy.on_tick(tick)
            
            # No order should be placed with insufficient data
            mock_adapter.place_order.assert_not_called()
            assert strategy.state.fast_sma is None
            assert strategy.state.slow_sma is None