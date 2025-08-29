"""
Strategy Hibernation Module v0.4.3
Natural selection for trading strategies.
Underperformers get benched, winners get more capital.
Because even good strategies have bad weeks, but bad strategies shouldn't get months.
"""

from decimal import Decimal
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple, Any
from datetime import datetime, timezone, timedelta
from enum import Enum
from collections import deque
import numpy as np
import logging
import json

logger = logging.getLogger(__name__)

class StrategyState(Enum):
    """The lifecycle of a trading strategy"""
    ACTIVE = "active"              # Currently trading
    HIBERNATING = "hibernating"    # Timeout for poor performance
    PROBATION = "probation"        # Recently returned, reduced size
    DISABLED = "disabled"          # Manually disabled
    TESTING = "testing"            # Paper trading only

class MarketRegime(Enum):
    """Market conditions"""
    TRENDING_UP = "trending_up"
    TRENDING_DOWN = "trending_down"
    RANGING = "ranging"
    VOLATILE = "volatile"
    QUIET = "quiet"

@dataclass
class StrategyPerformance:
    """Performance tracking for a strategy"""
    strategy_name: str
    state: StrategyState
    
    # Performance metrics
    total_trades: int = 0
    consecutive_wins: int = 0
    consecutive_losses: int = 0
    
    # Financial metrics
    total_pnl: Decimal = Decimal(0)
    total_r: Decimal = Decimal(0)  # Total R-multiple
    avg_win_r: Decimal = Decimal(0)
    avg_loss_r: Decimal = Decimal(0)
    
    # Risk metrics
    max_drawdown: Decimal = Decimal(0)
    current_drawdown: Decimal = Decimal(0)
    sharpe_ratio: float = 0.0
    
    # Regime performance
    regime_performance: Dict[MarketRegime, Dict] = field(default_factory=dict)
    
    # Hibernation tracking
    hibernation_count: int = 0
    last_hibernation: Optional[float] = None
    hibernation_end: Optional[float] = None
    
    # Recent trades for pattern analysis
    recent_trades: deque = field(default_factory=lambda: deque(maxlen=20))
    
    @property
    def win_rate(self) -> float:
        if self.total_trades == 0:
            return 0.0
        wins = len([t for t in self.recent_trades if t.get('pnl', 0) > 0])
        return wins / len(self.recent_trades) if self.recent_trades else 0.0
    
    @property
    def expectancy(self) -> Decimal:
        if self.total_trades == 0:
            return Decimal(0)
        return self.total_r / self.total_trades
    
    @property
    def is_hibernating(self) -> bool:
        if self.state != StrategyState.HIBERNATING:
            return False
        if self.hibernation_end:
            return datetime.now(timezone.utc).timestamp() < self.hibernation_end
        return False
    
    @property
    def time_until_active(self) -> float:
        """Seconds until strategy can trade again"""
        if not self.hibernation_end:
            return 0
        return max(0, self.hibernation_end - datetime.now(timezone.utc).timestamp())

@dataclass
class RegimeDetection:
    """Current market regime detection"""
    regime: MarketRegime
    confidence: float  # 0-1
    indicators: Dict[str, float]
    detected_at: float
    
    def to_dict(self) -> Dict:
        return {
            'regime': self.regime.value,
            'confidence': self.confidence,
            'indicators': self.indicators,
            'detected_at': self.detected_at
        }

class StrategyHibernationManager:
    """
    Manages strategy lifecycle based on performance.
    This is Darwinian selection for algorithms - adapt or get benched.
    """
    
    def __init__(self, config):
        self.config = config
        self.rotation_config = config.strategy_rotation
        
        # Strategy tracking
        self.strategies: Dict[str, StrategyPerformance] = {}
        
        # Current market regime
        self.current_regime: Optional[RegimeDetection] = None
        self.regime_history: deque = deque(maxlen=100)
        
        # Strategy weights (for capital allocation)
        self.strategy_weights: Dict[str, float] = {}
        
        # Hibernation events for audit
        self.hibernation_events: List[Dict] = []
        
        # Performance thresholds
        self.performance_window = timedelta(
            days=self.rotation_config.performance_window_days
        )
        
        logger.info("StrategyHibernationManager initialized - Natural selection active")
    
    def register_strategy(
        self,
        strategy_name: str,
        initial_weight: float = 0.33
    ) -> None:
        """Register a new strategy for tracking"""
        
        if strategy_name not in self.strategies:
            self.strategies[strategy_name] = StrategyPerformance(
                strategy_name=strategy_name,
                state=StrategyState.ACTIVE
            )
            
            self.strategy_weights[strategy_name] = initial_weight
            
            logger.info(f"Registered strategy: {strategy_name} (weight: {initial_weight:.2f})")
    
    def update_performance(
        self,
        strategy_name: str,
        trade_result: Dict[str, Any]
    ) -> Tuple[bool, Optional[str]]:
        """
        Update strategy performance and check for hibernation.
        Returns: (should_hibernate, reason)
        """
        
        if strategy_name not in self.strategies:
            self.register_strategy(strategy_name)
        
        strategy = self.strategies[strategy_name]
        
        # Skip if already hibernating
        if strategy.is_hibernating:
            return False, None
        
        # Update metrics
        strategy.total_trades += 1
        pnl = Decimal(str(trade_result['pnl']))
        r_multiple = Decimal(str(trade_result.get('r_multiple', 0)))
        
        strategy.total_pnl += pnl
        strategy.total_r += r_multiple
        
        # Update consecutive streaks
        if pnl > 0:
            strategy.consecutive_wins += 1
            strategy.consecutive_losses = 0
        else:
            strategy.consecutive_losses += 1
            strategy.consecutive_wins = 0
        
        # Add to recent trades
        strategy.recent_trades.append(trade_result)
        
        # Update regime performance
        if self.current_regime:
            regime = self.current_regime.regime
            if regime not in strategy.regime_performance:
                strategy.regime_performance[regime] = {
                    'trades': 0, 'pnl': Decimal(0), 'win_rate': 0
                }
            
            regime_perf = strategy.regime_performance[regime]
            regime_perf['trades'] += 1
            regime_perf['pnl'] += pnl
            
            # Update regime win rate
            regime_wins = len([
                t for t in strategy.recent_trades
                if t.get('regime') == regime.value and t.get('pnl', 0) > 0
            ])
            regime_perf['win_rate'] = regime_wins / regime_perf['trades']
        
        # Check hibernation conditions
        should_hibernate, reason = self._check_hibernation_conditions(strategy)
        
        if should_hibernate:
            self._hibernate_strategy(strategy, reason)
        
        # Update strategy weights based on performance
        self._update_strategy_weights()
        
        return should_hibernate, reason
    
    def _check_hibernation_conditions(
        self,
        strategy: StrategyPerformance
    ) -> Tuple[bool, Optional[str]]:
        """
        Check if strategy should be hibernated.
        Multiple conditions can trigger hibernation.
        """
        
        # Condition 1: Consecutive losses
        if strategy.consecutive_losses >= self.rotation_config.consecutive_losses_to_hibernate:
            return True, f"Consecutive losses: {strategy.consecutive_losses}"
        
        # Condition 2: Poor expectancy over window
        if strategy.total_trades >= 20:  # Need sufficient sample
            if strategy.expectancy < Decimal("0.1"):  # Less than 0.1R per trade
                return True, f"Poor expectancy: {strategy.expectancy:.2f}R"
        
        # Condition 3: Sharpe ratio below threshold
        if strategy.total_trades >= 30:
            strategy.sharpe_ratio = self._calculate_sharpe(strategy)
            if strategy.sharpe_ratio < self.rotation_config.min_sharpe_to_remain_active:
                return True, f"Low Sharpe ratio: {strategy.sharpe_ratio:.2f}"
        
        # Condition 4: Regime-specific failure
        if self.rotation_config.regime_adaptation_enabled and self.current_regime:
            regime_fail = self._check_regime_failure(strategy)
            if regime_fail:
                return True, f"Failing in {self.current_regime.regime.value} regime"
        
        # Condition 5: Excessive drawdown
        if strategy.current_drawdown > Decimal("0.06"):  # 6% strategy-specific DD
            return True, f"Excessive drawdown: {strategy.current_drawdown:.2%}"
        
        return False, None
    
    def _hibernate_strategy(
        self,
        strategy: StrategyPerformance,
        reason: str
    ) -> None:
        """Put a strategy into hibernation"""
        
        strategy.state = StrategyState.HIBERNATING
        strategy.hibernation_count += 1
        strategy.last_hibernation = datetime.now(timezone.utc).timestamp()
        
        # Calculate hibernation duration (increases with repeat offenses)
        base_hours = self.rotation_config.hibernation_cooldown_hours
        multiplier = min(strategy.hibernation_count, 3)  # Cap at 3x
        hibernation_hours = base_hours * multiplier
        
        strategy.hibernation_end = (
            datetime.now(timezone.utc) + timedelta(hours=hibernation_hours)
        ).timestamp()
        
        # Log hibernation event
        event = {
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'strategy': strategy.strategy_name,
            'reason': reason,
            'hibernation_number': strategy.hibernation_count,
            'duration_hours': hibernation_hours,
            'performance': {
                'expectancy': float(strategy.expectancy),
                'win_rate': strategy.win_rate,
                'consecutive_losses': strategy.consecutive_losses,
                'total_pnl': float(strategy.total_pnl)
            }
        }
        
        self.hibernation_events.append(event)
        
        logger.warning(f"""
        STRATEGY HIBERNATED
        Strategy: {strategy.strategy_name}
        Reason: {reason}
        Duration: {hibernation_hours} hours
        This is hibernation #{strategy.hibernation_count}
        """)
        
        # Set weight to zero
        self.strategy_weights[strategy.strategy_name] = 0
    
    def wake_strategy(self, strategy_name: str) -> bool:
        """
        Wake a strategy from hibernation (manual or automatic).
        Returns True if successful.
        """
        
        if strategy_name not in self.strategies:
            return False
        
        strategy = self.strategies[strategy_name]
        
        # Check if hibernation period is over
        if strategy.is_hibernating:
            if strategy.time_until_active > 0:
                logger.info(
                    f"Cannot wake {strategy_name} - "
                    f"{strategy.time_until_active/3600:.1f} hours remaining"
                )
                return False
        
        # Wake the strategy but put on probation
        strategy.state = StrategyState.PROBATION
        strategy.consecutive_losses = 0  # Reset loss counter
        
        # Give reduced weight initially
        base_weight = 1.0 / len([s for s in self.strategies.values() if s.state == StrategyState.ACTIVE])
        self.strategy_weights[strategy_name] = base_weight * 0.5  # Half weight on probation
        
        logger.info(f"Strategy {strategy_name} awakened - on probation with {self.strategy_weights[strategy_name]:.2f} weight")
        
        return True
    
    def detect_market_regime(
        self,
        market_data: Dict[str, Any]
    ) -> RegimeDetection:
        """
        Detect current market regime from market data.
        This determines which strategies should be active.
        """
        
        indicators = {}
        
        # Trend detection (simplified)
        sma_20 = market_data.get('sma_20', 0)
        sma_50 = market_data.get('sma_50', 0)
        price = market_data.get('close', 0)
        
        if price > sma_20 > sma_50:
            trend = 1.0  # Bullish
        elif price < sma_20 < sma_50:
            trend = -1.0  # Bearish
        else:
            trend = 0.0  # Neutral
        
        indicators['trend'] = trend
        
        # Volatility detection
        atr = market_data.get('atr', 0)
        atr_percentile = market_data.get('atr_percentile', 50)
        
        indicators['volatility'] = atr_percentile / 100
        
        # Volume analysis
        volume_ratio = market_data.get('volume_ratio', 1.0)  # Current vs average
        indicators['volume'] = volume_ratio
        
        # Determine regime
        if abs(trend) > 0.7 and atr_percentile < 70:
            if trend > 0:
                regime = MarketRegime.TRENDING_UP
            else:
                regime = MarketRegime.TRENDING_DOWN
            confidence = abs(trend)
            
        elif atr_percentile > 75:
            regime = MarketRegime.VOLATILE
            confidence = atr_percentile / 100
            
        elif atr_percentile < 25:
            regime = MarketRegime.QUIET
            confidence = (100 - atr_percentile) / 100
            
        else:
            regime = MarketRegime.RANGING
            confidence = 1.0 - abs(trend)
        
        detection = RegimeDetection(
            regime=regime,
            confidence=confidence,
            indicators=indicators,
            detected_at=datetime.now(timezone.utc).timestamp()
        )
        
        # Update current regime if significantly different
        if not self.current_regime or self.current_regime.regime != regime:
            self.current_regime = detection
            self.regime_history.append(detection)
            
            logger.info(f"Market regime changed to: {regime.value} (confidence: {confidence:.2f})")
            
            # Adjust strategy weights for new regime
            self._adjust_weights_for_regime(regime)
        
        return detection
    
    def _adjust_weights_for_regime(self, regime: MarketRegime) -> None:
        """
        Adjust strategy weights based on their regime performance.
        Strategies that perform well in current regime get more capital.
        """
        
        if not self.rotation_config.regime_adaptation_enabled:
            return
        
        for strategy_name, strategy in self.strategies.items():
            if strategy.state != StrategyState.ACTIVE:
                continue
            
            # Check historical performance in this regime
            if regime in strategy.regime_performance:
                regime_perf = strategy.regime_performance[regime]
                
                if regime_perf['trades'] >= 10:  # Need sufficient data
                    # Adjust weight based on regime-specific win rate
                    win_rate = regime_perf['win_rate']
                    
                    if win_rate > 0.6:  # Performs well in this regime
                        self.strategy_weights[strategy_name] *= 1.2
                    elif win_rate < 0.4:  # Performs poorly
                        self.strategy_weights[strategy_name] *= 0.7
        
        # Normalize weights
        self._normalize_weights()
    
    def _update_strategy_weights(self) -> None:
        """
        Update strategy weights based on recent performance.
        Winners get more capital, losers get less.
        """
        
        total_active = sum(
            1 for s in self.strategies.values()
            if s.state in [StrategyState.ACTIVE, StrategyState.PROBATION]
        )
        
        if total_active == 0:
            return
        
        # Calculate performance-based weights
        for strategy_name, strategy in self.strategies.items():
            if strategy.state == StrategyState.HIBERNATING:
                self.strategy_weights[strategy_name] = 0
                continue
            
            if strategy.state == StrategyState.DISABLED:
                self.strategy_weights[strategy_name] = 0
                continue
            
            # Base weight
            base_weight = 1.0 / total_active
            
            # Performance multiplier
            if strategy.total_trades >= 10:
                if strategy.expectancy > Decimal("0.5"):
                    multiplier = 1.3
                elif strategy.expectancy > Decimal("0.2"):
                    multiplier = 1.0
                else:
                    multiplier = 0.7
            else:
                multiplier = 0.9  # Slightly reduced for new strategies
            
            # Probation penalty
            if strategy.state == StrategyState.PROBATION:
                multiplier *= 0.5
            
            self.strategy_weights[strategy_name] = base_weight * multiplier
        
        # Normalize to sum to 1
        self._normalize_weights()
    
    def _normalize_weights(self) -> None:
        """Normalize weights to sum to 1"""
        
        total = sum(self.strategy_weights.values())
        if total > 0:
            for strategy_name in self.strategy_weights:
                self.strategy_weights[strategy_name] /= total
    
    def _calculate_sharpe(self, strategy: StrategyPerformance) -> float:
        """Calculate Sharpe ratio for strategy"""
        
        if not strategy.recent_trades:
            return 0.0
        
        returns = [float(t.get('r_multiple', 0)) for t in strategy.recent_trades]
        
        if len(returns) < 2:
            return 0.0
        
        mean_return = np.mean(returns)
        std_return = np.std(returns)
        
        if std_return == 0:
            return 0.0
        
        return mean_return / std_return * np.sqrt(252)  # Annualized
    
    def _check_regime_failure(self, strategy: StrategyPerformance) -> bool:
        """Check if strategy is failing in current regime"""
        
        if not self.current_regime:
            return False
        
        regime = self.current_regime.regime
        
        if regime not in strategy.regime_performance:
            return False  # No data yet
        
        regime_perf = strategy.regime_performance[regime]
        
        # Need at least 5 trades in regime to judge
        if regime_perf['trades'] < 5:
            return False
        
        # Failing if win rate < 30% in current regime
        return regime_perf['win_rate'] < 0.3
    
    def get_active_strategies(self) -> List[str]:
        """Get list of currently active strategies"""
        
        active = []
        
        for strategy_name, strategy in self.strategies.items():
            if strategy.state == StrategyState.ACTIVE:
                active.append(strategy_name)
            elif strategy.state == StrategyState.PROBATION:
                active.append(f"{strategy_name}*")  # Mark probation
        
        return active
    
    def get_strategy_allocations(self) -> Dict[str, float]:
        """Get current capital allocation percentages"""
        
        return {
            name: weight * 100
            for name, weight in self.strategy_weights.items()
            if weight > 0
        }
    
    def get_hibernation_report(self) -> Dict[str, Any]:
        """
        Generate comprehensive hibernation status report.
        This shows which strategies are benched and why.
        """
        
        report = {
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'current_regime': self.current_regime.to_dict() if self.current_regime else None,
            'active_strategies': [],
            'hibernating_strategies': [],
            'probation_strategies': [],
            'strategy_weights': {},
            'recent_hibernations': []
        }
        
        for strategy_name, strategy in self.strategies.items():
            strategy_info = {
                'name': strategy_name,
                'expectancy': float(strategy.expectancy),
                'win_rate': strategy.win_rate,
                'consecutive_losses': strategy.consecutive_losses,
                'total_trades': strategy.total_trades,
                'weight': self.strategy_weights.get(strategy_name, 0) * 100
            }
            
            if strategy.state == StrategyState.ACTIVE:
                report['active_strategies'].append(strategy_info)
                
            elif strategy.state == StrategyState.HIBERNATING:
                strategy_info['wake_in_hours'] = strategy.time_until_active / 3600
                strategy_info['hibernation_count'] = strategy.hibernation_count
                report['hibernating_strategies'].append(strategy_info)
                
            elif strategy.state == StrategyState.PROBATION:
                report['probation_strategies'].append(strategy_info)
        
        # Add weights
        report['strategy_weights'] = {
            k: f"{v*100:.1f}%"
            for k, v in self.strategy_weights.items()
        }
        
        # Recent hibernation events
        if self.hibernation_events:
            report['recent_hibernations'] = self.hibernation_events[-5:]  # Last 5
        
        return report
    
    def manual_override(
        self,
        strategy_name: str,
        action: str,
        reason: str = "Manual override"
    ) -> bool:
        """
        Manual strategy control (Angela's override).
        Actions: 'disable', 'enable', 'wake', 'hibernate'
        """
        
        if strategy_name not in self.strategies:
            return False
        
        strategy = self.strategies[strategy_name]
        
        if action == 'disable':
            strategy.state = StrategyState.DISABLED
            self.strategy_weights[strategy_name] = 0
            logger.info(f"Strategy {strategy_name} manually disabled: {reason}")
            
        elif action == 'enable':
            strategy.state = StrategyState.ACTIVE
            self._update_strategy_weights()
            logger.info(f"Strategy {strategy_name} manually enabled: {reason}")
            
        elif action == 'hibernate':
            self._hibernate_strategy(strategy, f"Manual: {reason}")
            
        elif action == 'wake':
            return self.wake_strategy(strategy_name)
        
        return True


# Example showing natural selection in action
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    # Mock configuration
    class MockRotationConfig:
        enabled = True
        consecutive_losses_to_hibernate = 5
        hibernation_cooldown_hours = 48
        performance_window_days = 20
        min_sharpe_to_remain_active = 0.5
        regime_adaptation_enabled = True
    
    class MockConfig:
        strategy_rotation = MockRotationConfig()
    
    config = MockConfig()
    
    # Create hibernation manager
    manager = StrategyHibernationManager(config)
    
    # Register strategies
    manager.register_strategy("London_Breakout", 0.33)
    manager.register_strategy("Volatility_Compression", 0.33)
    manager.register_strategy("Institutional_Flow", 0.34)
    
    print("="*60)
    print("STRATEGY HIBERNATION DEMONSTRATION")
    print("="*60)
    
    # Simulate London Breakout having a bad streak
    print("\n1. SIMULATING LOSS STREAK FOR LONDON BREAKOUT:")
    for i in range(5):
        should_hibernate, reason = manager.update_performance(
            "London_Breakout",
            {
                'pnl': -100,
                'r_multiple': -1.0,
                'symbol': 'EURUSD',
                'regime': 'ranging'
            }
        )
        print(f"  Loss #{i+1}: Hibernate? {should_hibernate}")
        if reason:
            print(f"  Reason: {reason}")
    
    # Simulate good performance for other strategies
    print("\n2. GOOD PERFORMANCE FOR VOLATILITY COMPRESSION:")
    for i in range(3):
        manager.update_performance(
            "Volatility_Compression",
            {
                'pnl': 200,
                'r_multiple': 2.0,
                'symbol': 'GBPUSD',
                'regime': 'volatile'
            }
        )
    
    # Detect market regime
    print("\n3. MARKET REGIME DETECTION:")
    regime = manager.detect_market_regime({
        'close': 1.1050,
        'sma_20': 1.1040,
        'sma_50': 1.1030,
        'atr': 0.0015,
        'atr_percentile': 65,
        'volume_ratio': 1.2
    })
    print(f"  Detected: {regime.regime.value}")
    print(f"  Confidence: {regime.confidence:.2f}")
    
    # Get current allocations
    print("\n4. CURRENT STRATEGY ALLOCATIONS:")
    allocations = manager.get_strategy_allocations()
    for strategy, weight in allocations.items():
        print(f"  {strategy}: {weight:.1f}%")
    
    # Generate report
    print("\n5. HIBERNATION REPORT:")
    report = manager.get_hibernation_report()
    print(f"  Active: {[s['name'] for s in report['active_strategies']]}")
    print(f"  Hibernating: {[s['name'] for s in report['hibernating_strategies']]}")
    print(f"  Weights: {report['strategy_weights']}")
