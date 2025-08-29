"""
Correlation-Aware Entry Filters v0.4.3
Because putting all your eggs in one basket is how empires fall.
This module prevents correlation-based concentration risk with mathematical precision.
"""

import numpy as np
import pandas as pd
from decimal import Decimal
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Set
from datetime import datetime, timezone, timedelta
from collections import defaultdict
import logging
import json

logger = logging.getLogger(__name__)

@dataclass
class CorrelationMatrix:
    """Rolling correlation matrix with time decay"""
    symbols: List[str]
    window_days: int
    correlations: np.ndarray  # NxN correlation matrix
    last_updated: float
    decay_factor: float = 0.8
    decay_hours: int = 4
    
    def get_correlation(self, symbol1: str, symbol2: str) -> float:
        """Get correlation between two symbols"""
        if symbol1 not in self.symbols or symbol2 not in self.symbols:
            return 0.0
        
        idx1 = self.symbols.index(symbol1)
        idx2 = self.symbols.index(symbol2)
        
        return float(self.correlations[idx1, idx2])
    
    def apply_time_decay(self, hours_elapsed: float) -> None:
        """Apply time decay to correlations"""
        if hours_elapsed > self.decay_hours:
            decay_periods = hours_elapsed / self.decay_hours
            decay_multiplier = self.decay_factor ** decay_periods
            
            # Decay correlations toward 0 (independence)
            self.correlations = self.correlations * decay_multiplier

@dataclass
class DXYLevel:
    """DXY (Dollar Index) support/resistance levels"""
    level: Decimal
    strength: str  # MAJOR/MINOR
    last_test: float
    respect_count: int  # How many times it's held
    
    def is_near(self, current_price: Decimal, tolerance_pct: Decimal) -> bool:
        """Check if price is near this level"""
        distance_pct = abs(current_price - self.level) / self.level
        return distance_pct <= tolerance_pct

@dataclass
class Position:
    """Active position for correlation tracking"""
    symbol: str
    direction: str  # BUY/SELL
    size: Decimal
    entry_price: Decimal
    entry_time: float
    risk_amount: Decimal
    cluster_id: Optional[str] = None
    
    @property
    def age_hours(self) -> float:
        """Position age in hours"""
        return (datetime.now(timezone.utc).timestamp() - self.entry_time) / 3600

class CorrelationFilter:
    """
    The guardian against correlation-based account destruction.
    Prevents you from taking 5 positions that are essentially the same trade.
    """
    
    def __init__(self, config):
        self.config = config
        self.correlation_config = config.correlation
        
        # Correlation tracking
        self.correlation_matrix: Optional[CorrelationMatrix] = None
        self.last_correlation_update: float = 0
        
        # DXY levels
        self.dxy_levels: List[DXYLevel] = self._initialize_dxy_levels()
        self.current_dxy: Optional[Decimal] = None
        
        # Position tracking
        self.active_positions: Dict[str, Position] = {}
        
        # Cluster risk tracking
        self.cluster_risks: Dict[str, Decimal] = defaultdict(Decimal)
        
        # Historical correlations for learning
        self.correlation_history: List[Dict] = []
        
        logger.info("CorrelationFilter initialized - Concentration risk protection active")
    
    def check_entry(
        self,
        symbol: str,
        direction: str,
        size: Decimal,
        risk_amount: Decimal
    ) -> Tuple[bool, Optional[str], Optional[Dict]]:
        """
        Main entry point - check if this trade would create dangerous correlation.
        Returns: (can_trade, rejection_reason, metadata)
        """
        
        if not self.correlation_config.enabled:
            return True, None, None
        
        metadata = {
            'symbol': symbol,
            'direction': direction,
            'checks_performed': []
        }
        
        # Check 1: DXY proximity for USD pairs
        if self._is_usd_pair(symbol):
            dxy_check = self._check_dxy_proximity(symbol, direction)
            metadata['checks_performed'].append('DXY_PROXIMITY')
            
            if not dxy_check[0]:
                return False, dxy_check[1], metadata
        
        # Check 2: Direct correlation with existing positions
        correlation_check = self._check_position_correlations(
            symbol, direction, risk_amount
        )
        metadata['checks_performed'].append('POSITION_CORRELATION')
        metadata['max_correlation'] = correlation_check[2]
        
        if not correlation_check[0]:
            return False, correlation_check[1], metadata
        
        # Check 3: Cluster risk limits
        cluster_id = self._get_cluster_id(symbol)
        if cluster_id:
            cluster_check = self._check_cluster_risk(
                cluster_id, risk_amount
            )
            metadata['checks_performed'].append('CLUSTER_RISK')
            metadata['cluster_id'] = cluster_id
            metadata['cluster_risk_after'] = float(
                self.cluster_risks[cluster_id] + risk_amount
            )
            
            if not cluster_check[0]:
                return False, cluster_check[1], metadata
        
        # Check 4: Time-decayed correlations
        self._apply_correlation_decay()
        
        # All checks passed
        metadata['result'] = 'APPROVED'
        return True, None, metadata
    
    def _check_dxy_proximity(
        self, 
        symbol: str, 
        direction: str
    ) -> Tuple[bool, Optional[str]]:
        """
        Check if DXY is near major S/R for USD pairs.
        This prevents entering USD trades when the dollar is at critical levels.
        """
        
        if not self.correlation_config.dxy_enabled:
            return True, None
        
        if not self.current_dxy:
            # No DXY data available
            return True, None
        
        # Find nearest S/R level
        nearest_level = None
        min_distance = Decimal("999")
        
        for level in self.dxy_levels:
            distance = abs(self.current_dxy - level.level)
            if distance < min_distance:
                min_distance = distance
                nearest_level = level
        
        if nearest_level and nearest_level.is_near(
            self.current_dxy, 
            self.correlation_config.dxy_sr_band_pct
        ):
            # DXY is at critical level
            if nearest_level.strength == "MAJOR":
                return False, (
                    f"DXY at major S/R level {nearest_level.level:.3f} "
                    f"(current: {self.current_dxy:.3f}). "
                    f"USD pairs blocked within {self.correlation_config.dxy_sr_band_pct:.1%} band"
                )
            else:
                # Minor level - just log warning
                logger.warning(
                    f"DXY near minor S/R {nearest_level.level:.3f}"
                )
        
        return True, None
    
    def _check_position_correlations(
        self,
        symbol: str,
        direction: str,
        risk_amount: Decimal
    ) -> Tuple[bool, Optional[str], float]:
        """
        Check correlation with existing positions.
        Prevents taking positions that are too correlated with what we already have.
        """
        
        if not self.correlation_matrix:
            return True, None, 0.0
        
        max_correlation = 0.0
        blocking_positions = []
        
        for pos_id, position in self.active_positions.items():
            # Get correlation between symbols
            correlation = self.correlation_matrix.get_correlation(
                symbol, position.symbol
            )
            
            # Apply time decay if position is old
            if position.age_hours > self.correlation_config.position_decay_hours:
                decay_factor = self.correlation_config.decay_factor
                correlation *= decay_factor
            
            # Check if same direction (correlation) or opposite (anti-correlation)
            if position.direction == direction:
                effective_correlation = abs(correlation)
            else:
                # Opposite directions with positive correlation = hedged
                # Opposite directions with negative correlation = doubled risk
                effective_correlation = abs(correlation) if correlation < 0 else 0
            
            max_correlation = max(max_correlation, effective_correlation)
            
            # Check against thresholds
            if effective_correlation >= self.correlation_config.correlation_block_threshold:
                blocking_positions.append({
                    'symbol': position.symbol,
                    'correlation': effective_correlation,
                    'age_hours': position.age_hours
                })
        
        if blocking_positions:
            positions_str = ", ".join([
                f"{p['symbol']} (corr: {p['correlation']:.2f})"
                for p in blocking_positions
            ])
            return False, (
                f"Position blocked due to high correlation with: {positions_str}. "
                f"Max correlation: {max_correlation:.2f} exceeds threshold "
                f"{self.correlation_config.correlation_block_threshold:.2f}"
            ), max_correlation
        
        # Check if we should reduce position size
        if max_correlation >= self.correlation_config.correlation_reduce_threshold:
            logger.warning(
                f"Consider reducing position size for {symbol}. "
                f"Correlation: {max_correlation:.2f}"
            )
        
        return True, None, max_correlation
    
    def _check_cluster_risk(
        self,
        cluster_id: str,
        new_risk: Decimal
    ) -> Tuple[bool, Optional[str]]:
        """
        Check if adding this risk to the cluster would exceed limits.
        Clusters are groups of highly correlated instruments.
        """
        
        current_cluster_risk = self.cluster_risks.get(cluster_id, Decimal(0))
        total_cluster_risk = current_cluster_risk + new_risk
        
        # Dynamic cluster limit based on number of positions
        num_positions = len([
            p for p in self.active_positions.values()
            if p.cluster_id == cluster_id
        ])
        
        # Base limit is 1.25x single position risk
        # But increases slightly with more positions (diversification benefit)
        diversity_multiplier = 1 + (0.1 * min(num_positions, 3))
        cluster_limit = new_risk * Decimal(str(1.25 * diversity_multiplier))
        
        if total_cluster_risk > cluster_limit:
            return False, (
                f"Cluster risk limit exceeded for {cluster_id}. "
                f"Current: ${current_cluster_risk:.2f}, "
                f"New would be: ${total_cluster_risk:.2f}, "
                f"Limit: ${cluster_limit:.2f}"
            )
        
        return True, None
    
    def update_correlation_matrix(
        self,
        price_data: pd.DataFrame
    ) -> None:
        """
        Update the rolling correlation matrix from price data.
        This should be called periodically (e.g., every hour).
        """
        
        # Calculate returns
        returns = price_data.pct_change().dropna()
        
        # Calculate correlation matrix
        correlation_df = returns.corr()
        
        # Create or update matrix object
        self.correlation_matrix = CorrelationMatrix(
            symbols=list(correlation_df.columns),
            window_days=self.correlation_config.correlation_window_days,
            correlations=correlation_df.values,
            last_updated=datetime.now(timezone.utc).timestamp(),
            decay_factor=self.correlation_config.decay_factor,
            decay_hours=self.correlation_config.position_decay_hours
        )
        
        self.last_correlation_update = self.correlation_matrix.last_updated
        
        # Log significant correlations
        self._log_significant_correlations()
    
    def _log_significant_correlations(self) -> None:
        """Log any dangerously high correlations"""
        if not self.correlation_matrix:
            return
        
        high_correlations = []
        
        for i, symbol1 in enumerate(self.correlation_matrix.symbols):
            for j, symbol2 in enumerate(self.correlation_matrix.symbols):
                if i >= j:  # Skip diagonal and duplicates
                    continue
                
                corr = self.correlation_matrix.correlations[i, j]
                
                if abs(corr) >= 0.8:
                    high_correlations.append({
                        'pair': f"{symbol1}/{symbol2}",
                        'correlation': corr
                    })
        
        if high_correlations:
            logger.warning(
                f"High correlations detected: {json.dumps(high_correlations, indent=2)}"
            )
    
    def add_position(
        self,
        position_id: str,
        symbol: str,
        direction: str,
        size: Decimal,
        entry_price: Decimal,
        risk_amount: Decimal
    ) -> None:
        """Add a new position to tracking"""
        
        cluster_id = self._get_cluster_id(symbol)
        
        position = Position(
            symbol=symbol,
            direction=direction,
            size=size,
            entry_price=entry_price,
            entry_time=datetime.now(timezone.utc).timestamp(),
            risk_amount=risk_amount,
            cluster_id=cluster_id
        )
        
        self.active_positions[position_id] = position
        
        # Update cluster risk
        if cluster_id:
            self.cluster_risks[cluster_id] += risk_amount
        
        logger.info(
            f"Added position: {symbol} {direction} "
            f"(risk: ${risk_amount:.2f}, cluster: {cluster_id})"
        )
    
    def remove_position(self, position_id: str) -> None:
        """Remove a closed position from tracking"""
        
        if position_id not in self.active_positions:
            return
        
        position = self.active_positions[position_id]
        
        # Update cluster risk
        if position.cluster_id:
            self.cluster_risks[position.cluster_id] -= position.risk_amount
            if self.cluster_risks[position.cluster_id] <= 0:
                del self.cluster_risks[position.cluster_id]
        
        del self.active_positions[position_id]
        
        logger.info(f"Removed position: {position.symbol}")
    
    def update_dxy(self, dxy_price: Decimal) -> None:
        """Update current DXY price"""
        self.current_dxy = dxy_price
        
        # Check if we're at any significant levels
        for level in self.dxy_levels:
            if level.is_near(dxy_price, Decimal("0.001")):  # Within 0.1%
                logger.info(
                    f"DXY at {level.strength} level {level.level:.3f} "
                    f"(current: {dxy_price:.3f})"
                )
                level.last_test = datetime.now(timezone.utc).timestamp()
                level.respect_count += 1
    
    def _apply_correlation_decay(self) -> None:
        """Apply time decay to correlation matrix"""
        
        if not self.correlation_matrix:
            return
        
        hours_elapsed = (
            datetime.now(timezone.utc).timestamp() - 
            self.correlation_matrix.last_updated
        ) / 3600
        
        if hours_elapsed > self.correlation_config.position_decay_hours:
            self.correlation_matrix.apply_time_decay(hours_elapsed)
            logger.debug(f"Applied correlation decay for {hours_elapsed:.1f} hours")
    
    def _get_cluster_id(self, symbol: str) -> Optional[str]:
        """Get cluster ID for a symbol"""
        
        for cluster_id, symbols in self.correlation_config.clusters.items():
            if symbol in symbols:
                return cluster_id
        
        # Check for currency-based clustering
        if "USD" in symbol and symbol not in ["XAUUSD", "XAGUSD"]:
            return "USD_MAJORS"
        elif "JPY" in symbol:
            return "JPY_CROSSES"
        elif "EUR" in symbol and "USD" not in symbol:
            return "EUR_CROSSES"
        
        return None
    
    def _is_usd_pair(self, symbol: str) -> bool:
        """Check if symbol involves USD"""
        return "USD" in symbol
    
    def _initialize_dxy_levels(self) -> List[DXYLevel]:
        """Initialize major DXY support/resistance levels"""
        
        # Historical major levels for DXY
        levels = [
            DXYLevel(Decimal("90.00"), "MAJOR", 0, 0),   # Psychological
            DXYLevel(Decimal("92.50"), "MINOR", 0, 0),
            DXYLevel(Decimal("95.00"), "MAJOR", 0, 0),   # Historical resistance
            DXYLevel(Decimal("97.50"), "MINOR", 0, 0),
            DXYLevel(Decimal("100.00"), "MAJOR", 0, 0),  # Psychological
            DXYLevel(Decimal("102.50"), "MINOR", 0, 0),
            DXYLevel(Decimal("105.00"), "MAJOR", 0, 0),  # 2022 high area
            DXYLevel(Decimal("107.50"), "MINOR", 0, 0),
            DXYLevel(Decimal("110.00"), "MAJOR", 0, 0),  # Major resistance
        ]
        
        return levels
    
    def get_correlation_report(self) -> Dict[str, Any]:
        """
        Generate a correlation report for the dashboard.
        This shows current correlation state and risks.
        """
        
        report = {
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'active_positions': len(self.active_positions),
            'cluster_risks': {
                cluster: float(risk)
                for cluster, risk in self.cluster_risks.items()
            },
            'current_dxy': float(self.current_dxy) if self.current_dxy else None,
            'high_correlations': [],
            'position_ages': {}
        }
        
        # Add position ages
        for pos_id, position in self.active_positions.items():
            report['position_ages'][position.symbol] = {
                'age_hours': position.age_hours,
                'decayed': position.age_hours > self.correlation_config.position_decay_hours
            }
        
        # Find high correlations among active positions
        if self.correlation_matrix and len(self.active_positions) > 1:
            positions = list(self.active_positions.values())
            
            for i, pos1 in enumerate(positions):
                for j, pos2 in enumerate(positions[i+1:], i+1):
                    corr = self.correlation_matrix.get_correlation(
                        pos1.symbol, pos2.symbol
                    )
                    
                    if abs(corr) >= 0.5:  # Report correlations above 0.5
                        report['high_correlations'].append({
                            'pair': f"{pos1.symbol}/{pos2.symbol}",
                            'correlation': corr,
                            'risk': 'HIGH' if abs(corr) >= 0.7 else 'MODERATE'
                        })
        
        return report
    
    def simulate_position(
        self,
        symbol: str,
        direction: str,
        risk_amount: Decimal
    ) -> Dict[str, Any]:
        """
        Simulate adding a position to see correlation impact.
        Useful for "what-if" analysis.
        """
        
        # Run all checks without actually adding the position
        can_trade, reason, metadata = self.check_entry(
            symbol, direction, Decimal("100000"), risk_amount
        )
        
        simulation = {
            'symbol': symbol,
            'direction': direction,
            'risk_amount': float(risk_amount),
            'can_trade': can_trade,
            'rejection_reason': reason,
            'metadata': metadata
        }
        
        if can_trade and self.correlation_matrix:
            # Calculate what correlations would be
            correlations_after = {}
            
            for pos_id, position in self.active_positions.items():
                corr = self.correlation_matrix.get_correlation(
                    symbol, position.symbol
                )
                correlations_after[position.symbol] = corr
            
            simulation['correlations_after'] = correlations_after
            
            # Calculate new cluster risk
            cluster_id = self._get_cluster_id(symbol)
            if cluster_id:
                simulation['cluster_risk_after'] = float(
                    self.cluster_risks.get(cluster_id, Decimal(0)) + risk_amount
                )
        
        return simulation


# Example usage showing correlation prevention in action
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    # Mock configuration
    class MockConfig:
        class CorrelationConfig:
            enabled = True
            dxy_sr_band_pct = Decimal("0.002")
            dxy_enabled = True
            correlation_window_days = 20
            correlation_block_threshold = 0.70
            correlation_reduce_threshold = 0.50
            position_decay_hours = 4
            decay_factor = 0.8
            clusters = {
                "USD_MAJORS": ["EURUSD", "GBPUSD", "AUDUSD"],
                "INDICES": ["US30", "NAS100", "SPX500"]
            }
    
    config = MockConfig()
    config.correlation = MockConfig.CorrelationConfig()
    
    # Create filter
    filter = CorrelationFilter(config)
    
    # Update DXY
    filter.update_dxy(Decimal("105.05"))  # Near major resistance
    
    # Create mock correlation matrix
    symbols = ["EURUSD", "GBPUSD", "AUDUSD", "USDJPY", "XAUUSD"]
    correlations = np.array([
        [1.00, 0.85, 0.75, -0.60, 0.40],  # EURUSD
        [0.85, 1.00, 0.70, -0.55, 0.35],  # GBPUSD
        [0.75, 0.70, 1.00, -0.50, 0.45],  # AUDUSD
        [-0.60, -0.55, -0.50, 1.00, -0.30],  # USDJPY
        [0.40, 0.35, 0.45, -0.30, 1.00],  # XAUUSD
    ])
    
    filter.correlation_matrix = CorrelationMatrix(
        symbols=symbols,
        window_days=20,
        correlations=correlations,
        last_updated=datetime.now(timezone.utc).timestamp()
    )
    
    # Add some existing positions
    filter.add_position(
        "POS001", "EURUSD", "BUY",
        Decimal("100000"), Decimal("1.1000"), Decimal("500")
    )
    
    print("="*60)
    print("CORRELATION FILTER TESTS")
    print("="*60)
    
    # Test 1: Try to add highly correlated position
    print("\nTest 1: Adding GBPUSD (high correlation with EURUSD)")
    can_trade, reason, metadata = filter.check_entry(
        "GBPUSD", "BUY", Decimal("100000"), Decimal("500")
    )
    print(f"Can trade: {can_trade}")
    if reason:
        print(f"Reason: {reason}")
    print(f"Metadata: {json.dumps(metadata, indent=2, default=str)}")
    
    # Test 2: Try to add uncorrelated position
    print("\nTest 2: Adding XAUUSD (lower correlation)")
    can_trade, reason, metadata = filter.check_entry(
        "XAUUSD", "BUY", Decimal("10"), Decimal("500")
    )
    print(f"Can trade: {can_trade}")
    if reason:
        print(f"Reason: {reason}")
    
    # Test 3: Check DXY blocking
    print("\nTest 3: DXY near major level")
    filter.update_dxy(Decimal("105.00"))  # Exactly at major level
    can_trade, reason, metadata = filter.check_entry(
        "AUDUSD", "SELL", Decimal("100000"), Decimal("500")
    )
    print(f"Can trade: {can_trade}")
    if reason:
        print(f"Reason: {reason}")
    
    # Generate report
    print("\nCORRELATION REPORT:")
    report = filter.get_correlation_report()
    print(json.dumps(report, indent=2, default=str))
