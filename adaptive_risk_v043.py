"""
Adaptive Risk Sizing Module v0.4.3
Because static risk in dynamic markets is how peasants trade.
This module makes risk sizing intelligent, adaptive, and ruthlessly effective.
"""

from decimal import Decimal, ROUND_DOWN
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime, timezone, timedelta
from enum import Enum
from collections import deque
import logging
import json
import numpy as np

logger = logging.getLogger(__name__)

class PerformanceState(Enum):
    """Current performance trajectory"""
    HOT_STREAK = "hot_streak"        # Multiple wins, increase aggression
    COLD_STREAK = "cold_streak"      # Multiple losses, preserve capital  
    NEUTRAL = "neutral"              # Mixed results, standard risk
    RECOVERING = "recovering"        # Coming back from drawdown
    PEAK = "peak"                    # At equity highs, be careful

class SignalStrength(Enum):
    """How confident are we in this signal?"""
    EXTREME = 4     # All stars aligned
    STRONG = 3      # High conviction
    MODERATE = 2    # Decent setup
    WEAK = 1        # Marginal edge

@dataclass
class TradeResult:
    """Historical trade for performance tracking"""
    trade_id: str
    symbol: str
    strategy: str
    entry_time: float
    exit_time: float
    pnl: Decimal
    pnl_r: Decimal  # P&L in R (risk units)
    signal_strength: SignalStrength
    
    @property
    def is_win(self) -> bool:
        return self.pnl > 0
    
    @property
    def duration_hours(self) -> float:
        return (self.exit_time - self.entry_time) / 3600

@dataclass
class PerformanceMetrics:
    """Rolling performance metrics for adaptation"""
    total_trades: int = 0
    wins: int = 0
    losses: int = 0
    
    current_streak: int = 0  # Positive = win streak, Negative = loss streak
    max_win_streak: int = 0
    max_loss_streak: int = 0
    
    total_pnl: Decimal = Decimal(0)
    total_r: Decimal = Decimal(0)
    
    avg_win: Decimal = Decimal(0)
    avg_loss: Decimal = Decimal(0)
    
    sharpe_ratio: float = 0.0
    profit_factor: float = 0.0
    recovery_factor: float = 0.0
    
    @property
    def win_rate(self) -> float:
        if self.total_trades == 0:
            return 0.0
        return self.wins / self.total_trades
    
    @property
    def expectancy(self) -> Decimal:
        """Expected value per trade in R"""
        if self.total_trades == 0:
            return Decimal(0)
        return self.total_r / self.total_trades

class AdaptiveRiskEngine:
    """
    The intelligence that makes risk sizing respond to market conditions.
    When you're winning, press harder. When you're losing, protect capital.
    But always, ALWAYS respect the guards.
    """
    
    def __init__(self, config):
        self.config = config
        self.risk_config = config.risk
        
        # Performance tracking
        self.recent_trades = deque(maxlen=100)  # Last 100 trades
        self.performance = PerformanceMetrics()
        self.performance_by_strategy: Dict[str, PerformanceMetrics] = {}
        
        # State tracking
        self.current_state = PerformanceState.NEUTRAL
        self.equity_curve: List[Decimal] = []
        self.peak_equity: Decimal = Decimal(0)
        self.current_drawdown: Decimal = Decimal(0)
        
        # Risk adaptation history
        self.risk_history: List[Dict] = []
        self.adaptation_events: List[Dict] = []
        
        # Angela Override tracking
        self.angela_override_active: bool = False
        self.angela_risk_override: Optional[Decimal] = None
        
        logger.info("AdaptiveRiskEngine initialized - Intelligence activated")
    
    def calculate_position_risk(
        self,
        base_risk_pct: Decimal,
        signal_strength: SignalStrength,
        strategy_name: str,
        symbol: str
    ) -> Tuple[Decimal, Dict[str, Any]]:
        """
        Calculate adaptive position risk based on current conditions.
        This is where mathematics meets psychology meets profit.
        
        Returns: (risk_percentage, metadata)
        """
        
        metadata = {
            'base_risk': float(base_risk_pct),
            'signal_strength': signal_strength.name,
            'strategy': strategy_name,
            'symbol': symbol,
            'adaptations': []
        }
        
        # Check for Angela Override first - sovereign power
        if self.angela_override_active and self.angela_risk_override:
            metadata['angela_override'] = True
            metadata['final_risk'] = float(self.angela_risk_override)
            return self.angela_risk_override, metadata
        
        # Start with base risk
        if self.risk_config.mode == RiskMode.FIXED:
            # Fixed mode - only adjust for signal strength
            risk_pct = self.risk_config.fixed_pct
            metadata['mode'] = 'FIXED'
        else:
            # Adaptive mode - this is where it gets interesting
            risk_pct = self._calculate_adaptive_risk(
                base_risk_pct, signal_strength, strategy_name, metadata
            )
            metadata['mode'] = 'ADAPTIVE'
        
        # Apply signal strength multiplier
        strength_mult = self.risk_config.signal_strength_multipliers.get(
            signal_strength.name, 1.0
        )
        risk_pct = risk_pct * Decimal(str(strength_mult))
        metadata['strength_multiplier'] = strength_mult
        
        # Apply strategy-specific adjustments
        strategy_adjustment = self._get_strategy_adjustment(strategy_name)
        risk_pct = risk_pct * strategy_adjustment
        metadata['strategy_adjustment'] = float(strategy_adjustment)
        
        # Enforce absolute limits
        risk_pct = max(
            self.risk_config.adaptive_floor_pct,
            min(risk_pct, self.risk_config.adaptive_ceiling_pct)
        )
        
        metadata['final_risk'] = float(risk_pct)
        
        # Log significant adaptations
        if abs(float(risk_pct - base_risk_pct)) > 0.002:  # 0.2% change
            self._log_adaptation(risk_pct, base_risk_pct, metadata)
        
        return risk_pct, metadata
    
    def _calculate_adaptive_risk(
        self,
        base_risk: Decimal,
        signal_strength: SignalStrength,
        strategy: str,
        metadata: Dict
    ) -> Decimal:
        """
        The core adaptive algorithm.
        This is where we breathe with the market.
        """
        
        risk = base_risk
        
        # 1. Streak-based adaptation
        if self.performance.current_streak >= self.risk_config.adaptive_win_streak_threshold:
            # Win streak - increase aggression
            streak_multiplier = 1 + (0.1 * (self.performance.current_streak - 2))
            streak_multiplier = min(1.3, streak_multiplier)  # Cap at 30% increase
            risk = risk * Decimal(str(streak_multiplier))
            metadata['adaptations'].append({
                'type': 'WIN_STREAK',
                'streak': self.performance.current_streak,
                'multiplier': streak_multiplier
            })
            
        elif abs(self.performance.current_streak) >= self.risk_config.adaptive_loss_streak_threshold:
            # Loss streak - reduce risk
            streak_divisor = 1 + (0.15 * (abs(self.performance.current_streak) - 1))
            risk = risk / Decimal(str(streak_divisor))
            metadata['adaptations'].append({
                'type': 'LOSS_STREAK',
                'streak': self.performance.current_streak,
                'divisor': streak_divisor
            })
        
        # 2. Equity curve adaptation
        if self.current_drawdown > Decimal("0.02"):  # In drawdown > 2%
            # Reduce risk proportionally to drawdown
            dd_reduction = 1 - (float(self.current_drawdown) * 2)  # 2x multiplier
            dd_reduction = max(0.5, dd_reduction)  # Never reduce by more than 50%
            risk = risk * Decimal(str(dd_reduction))
            metadata['adaptations'].append({
                'type': 'DRAWDOWN_REDUCTION',
                'drawdown': float(self.current_drawdown),
                'reduction': dd_reduction
            })
            
        elif self._at_equity_peak():
            # At all-time high - slightly conservative
            risk = risk * Decimal("0.9")
            metadata['adaptations'].append({
                'type': 'PEAK_CAUTION',
                'reduction': 0.9
            })
        
        # 3. Performance state adaptation
        state_multipliers = {
            PerformanceState.HOT_STREAK: Decimal("1.2"),
            PerformanceState.COLD_STREAK: Decimal("0.7"),
            PerformanceState.NEUTRAL: Decimal("1.0"),
            PerformanceState.RECOVERING: Decimal("0.85"),
            PerformanceState.PEAK: Decimal("0.95")
        }
        
        state_mult = state_multipliers.get(self.current_state, Decimal("1.0"))
        risk = risk * state_mult
        metadata['adaptations'].append({
            'type': 'PERFORMANCE_STATE',
            'state': self.current_state.value,
            'multiplier': float(state_mult)
        })
        
        # 4. Time-of-day adaptation (lower risk during news windows)
        time_mult = self._get_time_of_day_multiplier()
        if time_mult != 1.0:
            risk = risk * Decimal(str(time_mult))
            metadata['adaptations'].append({
                'type': 'TIME_OF_DAY',
                'multiplier': time_mult
            })
        
        # 5. Volatility regime adaptation
        vol_mult = self._get_volatility_multiplier()
        if vol_mult != 1.0:
            risk = risk * Decimal(str(vol_mult))
            metadata['adaptations'].append({
                'type': 'VOLATILITY_REGIME', 
                'multiplier': vol_mult
            })
        
        return risk
    
    def update_performance(self, trade_result: TradeResult) -> None:
        """
        Update performance metrics with a completed trade.
        This is how the system learns.
        """
        
        # Add to recent trades
        self.recent_trades.append(trade_result)
        
        # Update overall metrics
        self._update_metrics(self.performance, trade_result)
        
        # Update strategy-specific metrics
        if trade_result.strategy not in self.performance_by_strategy:
            self.performance_by_strategy[trade_result.strategy] = PerformanceMetrics()
        
        self._update_metrics(
            self.performance_by_strategy[trade_result.strategy],
            trade_result
        )
        
        # Update equity curve
        if self.equity_curve:
            new_equity = self.equity_curve[-1] + trade_result.pnl
        else:
            new_equity = Decimal("100000") + trade_result.pnl  # Assume 100k starting
        
        self.equity_curve.append(new_equity)
        
        # Update peak and drawdown
        if new_equity > self.peak_equity:
            self.peak_equity = new_equity
            self.current_drawdown = Decimal(0)
        else:
            self.current_drawdown = (self.peak_equity - new_equity) / self.peak_equity
        
        # Update performance state
        self._update_performance_state()
        
        logger.info(
            f"Performance updated: {trade_result.symbol} "
            f"{'WIN' if trade_result.is_win else 'LOSS'} "
            f"${trade_result.pnl:.2f} ({trade_result.pnl_r:.2f}R) "
            f"Streak: {self.performance.current_streak}"
        )
    
    def _update_metrics(
        self,
        metrics: PerformanceMetrics,
        trade: TradeResult
    ) -> None:
        """Update a metrics object with trade results"""
        
        metrics.total_trades += 1
        
        if trade.is_win:
            metrics.wins += 1
            
            # Update streak
            if metrics.current_streak >= 0:
                metrics.current_streak += 1
            else:
                metrics.current_streak = 1
            
            metrics.max_win_streak = max(
                metrics.max_win_streak,
                metrics.current_streak
            )
            
            # Update averages
            if metrics.wins == 1:
                metrics.avg_win = trade.pnl
            else:
                metrics.avg_win = (
                    (metrics.avg_win * (metrics.wins - 1) + trade.pnl) /
                    metrics.wins
                )
        else:
            metrics.losses += 1
            
            # Update streak
            if metrics.current_streak <= 0:
                metrics.current_streak -= 1
            else:
                metrics.current_streak = -1
            
            metrics.max_loss_streak = max(
                metrics.max_loss_streak,
                abs(metrics.current_streak)
            )
            
            # Update averages
            if metrics.losses == 1:
                metrics.avg_loss = abs(trade.pnl)
            else:
                metrics.avg_loss = (
                    (metrics.avg_loss * (metrics.losses - 1) + abs(trade.pnl)) /
                    metrics.losses
                )
        
        # Update totals
        metrics.total_pnl += trade.pnl
        metrics.total_r += trade.pnl_r
        
        # Calculate derived metrics
        self._calculate_derived_metrics(metrics)
    
    def _calculate_derived_metrics(self, metrics: PerformanceMetrics) -> None:
        """Calculate Sharpe, profit factor, etc."""
        
        if len(self.recent_trades) > 10:
            # Calculate Sharpe ratio (simplified)
            returns = [float(t.pnl_r) for t in self.recent_trades]
            if len(returns) > 1:
                metrics.sharpe_ratio = (
                    np.mean(returns) / np.std(returns)
                    if np.std(returns) > 0 else 0
                )
        
        # Profit factor
        if metrics.losses > 0 and metrics.avg_loss > 0:
            total_wins = metrics.wins * metrics.avg_win
            total_losses = metrics.losses * metrics.avg_loss
            metrics.profit_factor = float(total_wins / total_losses)
    
    def _update_performance_state(self) -> None:
        """
        Determine current performance state.
        This is the system's self-awareness.
        """
        
        old_state = self.current_state
        
        # Hot streak detection
        if self.performance.current_streak >= 4:
            self.current_state = PerformanceState.HOT_STREAK
            
        # Cold streak detection
        elif abs(self.performance.current_streak) >= 3:
            self.current_state = PerformanceState.COLD_STREAK
            
        # Peak detection
        elif self._at_equity_peak() and self.performance.total_trades > 20:
            self.current_state = PerformanceState.PEAK
            
        # Recovery detection
        elif self.current_drawdown > Decimal("0.02") and self.performance.current_streak > 0:
            self.current_state = PerformanceState.RECOVERING
            
        # Default to neutral
        else:
            self.current_state = PerformanceState.NEUTRAL
        
        if old_state != self.current_state:
            logger.info(
                f"Performance state changed: {old_state.value} -> {self.current_state.value}"
            )
            
            self.adaptation_events.append({
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'event': 'STATE_CHANGE',
                'from': old_state.value,
                'to': self.current_state.value,
                'metrics': {
                    'streak': self.performance.current_streak,
                    'drawdown': float(self.current_drawdown),
                    'win_rate': self.performance.win_rate
                }
            })
    
    def _get_strategy_adjustment(self, strategy: str) -> Decimal:
        """
        Get risk adjustment for specific strategy based on its performance.
        Good strategies get more capital, bad ones get benched.
        """
        
        if strategy not in self.performance_by_strategy:
            return Decimal("1.0")
        
        perf = self.performance_by_strategy[strategy]
        
        # Need at least 10 trades to judge
        if perf.total_trades < 10:
            return Decimal("0.9")  # Slightly conservative for new strategies
        
        # Adjust based on expectancy
        if perf.expectancy > Decimal("0.5"):  # Very profitable
            return Decimal("1.1")
        elif perf.expectancy > Decimal("0.2"):  # Profitable
            return Decimal("1.0")
        elif perf.expectancy > Decimal("0"):  # Marginally profitable
            return Decimal("0.8")
        else:  # Losing
            return Decimal("0.6")
    
    def _at_equity_peak(self) -> bool:
        """Check if we're at or near equity peak"""
        if not self.equity_curve:
            return False
        
        current = self.equity_curve[-1]
        return current >= self.peak_equity * Decimal("0.995")  # Within 0.5% of peak
    
    def _get_time_of_day_multiplier(self) -> float:
        """
        Adjust risk based on time of day.
        Lower risk during news windows, higher during optimal sessions.
        """
        
        current_hour = datetime.now(timezone.utc).hour
        
        # London session (7-9 UTC) - optimal
        if 7 <= current_hour <= 9:
            return 1.1
        
        # US session (13-15 UTC) - good
        elif 13 <= current_hour <= 15:
            return 1.05
        
        # News window protection (around major releases)
        elif current_hour in [12, 14, 19]:  # Common news times
            return 0.8
        
        # Asian session - lower volatility typically
        elif 22 <= current_hour or current_hour <= 6:
            return 0.9
        
        return 1.0
    
    def _get_volatility_multiplier(self) -> float:
        """
        Adjust risk based on market volatility regime.
        High vol = lower risk, Low vol = standard risk.
        """
        
        # This would connect to actual volatility data
        # For now, return neutral
        return 1.0
    
    def _log_adaptation(
        self,
        final_risk: Decimal,
        base_risk: Decimal,
        metadata: Dict
    ) -> None:
        """Log significant risk adaptations"""
        
        adaptation = {
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'base_risk': float(base_risk),
            'final_risk': float(final_risk),
            'change_pct': float((final_risk - base_risk) / base_risk * 100),
            'metadata': metadata
        }
        
        self.risk_history.append(adaptation)
        
        # Keep only last 1000 adaptations
        if len(self.risk_history) > 1000:
            self.risk_history = self.risk_history[-1000:]
    
    def set_angela_override(
        self,
        risk_pct: Optional[Decimal] = None,
        active: bool = True
    ) -> None:
        """
        Angela's sovereign override of risk sizing.
        When the queen speaks, the system obeys.
        """
        
        self.angela_override_active = active
        self.angela_risk_override = risk_pct
        
        if active:
            logger.critical(
                f"ANGELA OVERRIDE ACTIVE - Risk set to {risk_pct:.2%}"
            )
            
            self.adaptation_events.append({
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'event': 'ANGELA_OVERRIDE',
                'risk_pct': float(risk_pct) if risk_pct else None,
                'active': active
            })
    
    def get_performance_report(self) -> Dict[str, Any]:
        """
        Generate comprehensive performance report.
        This is the system's self-assessment.
        """
        
        report = {
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'overall': {
                'total_trades': self.performance.total_trades,
                'win_rate': self.performance.win_rate,
                'expectancy_r': float(self.performance.expectancy),
                'current_streak': self.performance.current_streak,
                'sharpe_ratio': self.performance.sharpe_ratio,
                'profit_factor': self.performance.profit_factor,
                'total_pnl': float(self.performance.total_pnl),
                'avg_win': float(self.performance.avg_win),
                'avg_loss': float(self.performance.avg_loss)
            },
            'state': {
                'current': self.current_state.value,
                'drawdown': float(self.current_drawdown),
                'at_peak': self._at_equity_peak()
            },
            'by_strategy': {}
        }
        
        # Add strategy-specific performance
        for strategy, perf in self.performance_by_strategy.items():
            report['by_strategy'][strategy] = {
                'trades': perf.total_trades,
                'win_rate': perf.win_rate,
                'expectancy_r': float(perf.expectancy),
                'streak': perf.current_streak
            }
        
        # Add recent adaptations
        if self.risk_history:
            recent = self.risk_history[-5:]  # Last 5 adaptations
            report['recent_adaptations'] = recent
        
        return report
    
    def simulate_risk_adaptation(
        self,
        signal_strength: SignalStrength,
        strategy: str
    ) -> Dict[str, Any]:
        """
        Simulate what risk would be assigned.
        Useful for testing and Angela's preview.
        """
        
        base_risk = self.risk_config.fixed_pct
        risk_pct, metadata = self.calculate_position_risk(
            base_risk,
            signal_strength,
            strategy,
            "EURUSD"  # Example symbol
        )
        
        simulation = {
            'base_risk_pct': float(base_risk),
            'adapted_risk_pct': float(risk_pct),
            'change_pct': float((risk_pct - base_risk) / base_risk * 100),
            'current_state': self.current_state.value,
            'current_streak': self.performance.current_streak,
            'metadata': metadata
        }
        
        return simulation


# Example showing adaptive risk in action
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    # Mock configuration
    from enum import Enum
    
    class RiskMode(Enum):
        FIXED = "fixed"
        ADAPTIVE = "adaptive"
    
    class MockRiskConfig:
        mode = RiskMode.ADAPTIVE
        fixed_pct = Decimal("0.006")
        adaptive_win_streak_threshold = 3
        adaptive_loss_streak_threshold = 2
        adaptive_floor_pct = Decimal("0.004")
        adaptive_ceiling_pct = Decimal("0.008")
        signal_strength_multipliers = {
            "EXTREME": 1.0,
            "STRONG": 0.8,
            "MODERATE": 0.6,
            "WEAK": 0.0
        }
    
    class MockConfig:
        risk = MockRiskConfig()
    
    config = MockConfig()
    
    # Create adaptive engine
    engine = AdaptiveRiskEngine(config)
    
    print("="*60)
    print("ADAPTIVE RISK ENGINE DEMONSTRATION")
    print("="*60)
    
    # Simulate a winning streak
    print("\n1. SIMULATING WIN STREAK:")
    for i in range(4):
        trade = TradeResult(
            trade_id=f"WIN{i+1}",
            symbol="EURUSD",
            strategy="London_Breakout",
            entry_time=datetime.now(timezone.utc).timestamp() - 3600,
            exit_time=datetime.now(timezone.utc).timestamp(),
            pnl=Decimal("250"),
            pnl_r=Decimal("2.5"),
            signal_strength=SignalStrength.STRONG
        )
        engine.update_performance(trade)
    
    # Calculate risk after win streak
    risk, meta = engine.calculate_position_risk(
        Decimal("0.006"),
        SignalStrength.STRONG,
        "London_Breakout",
        "EURUSD"
    )
    
    print(f"After 4 wins:")
    print(f"  Base risk: 0.6%")
    print(f"  Adapted risk: {risk:.3%}")
    print(f"  State: {engine.current_state.value}")
    print(f"  Adaptations: {json.dumps(meta['adaptations'], indent=2)}")
    
    # Simulate a loss
    print("\n2. SIMULATING LOSS:")
    loss_trade = TradeResult(
        trade_id="LOSS1",
        symbol="GBPUSD",
        strategy="London_Breakout",
        entry_time=datetime.now(timezone.utc).timestamp() - 3600,
        exit_time=datetime.now(timezone.utc).timestamp(),
        pnl=Decimal("-100"),
        pnl_r=Decimal("-1.0"),
        signal_strength=SignalStrength.MODERATE
    )
    engine.update_performance(loss_trade)
    
    risk, meta = engine.calculate_position_risk(
        Decimal("0.006"),
        SignalStrength.MODERATE,
        "London_Breakout",
        "GBPUSD"
    )
    
    print(f"After 1 loss (breaking streak):")
    print(f"  Adapted risk: {risk:.3%}")
    print(f"  State: {engine.current_state.value}")
    
    # Test Angela Override
    print("\n3. ANGELA OVERRIDE:")
    engine.set_angela_override(Decimal("0.01"), active=True)
    
    risk, meta = engine.calculate_position_risk(
        Decimal("0.006"),
        SignalStrength.WEAK,
        "Any_Strategy",
        "XAUUSD"
    )
    
    print(f"With Angela Override:")
    print(f"  Angela says: 1.0%")
    print(f"  System obeys: {risk:.3%}")
    print(f"  Override flag: {meta.get('angela_override', False)}")
    
    # Generate performance report
    print("\n4. PERFORMANCE REPORT:")
    report = engine.get_performance_report()
    print(json.dumps(report, indent=2, default=str))
