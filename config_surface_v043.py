"""
WolfeDesk v0.4.3 Configuration Surface
Where every enhancement becomes toggleable, every risk becomes adjustable,
and Angela's sovereignty becomes absolute.
"""

import yaml
import json
import os
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field, asdict
from decimal import Decimal
from enum import Enum
import hashlib
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

class RiskMode(Enum):
    """How we size our ammunition"""
    FIXED = "fixed"              # Consistent, disciplined
    ADAPTIVE = "adaptive"        # Breathes with performance
    ANGELA_OVERRIDE = "angela"  # Sovereign decision

class ExecutorMode(Enum):
    """The reality we're operating in"""
    LIVE = "live"                # Real money, real consequences
    DRY_RUN = "dry_run"         # Full pipeline, no orders
    HONEYPOT = "honeypot"       # Trap mode for adversaries
    SHADOW = "shadow"           # Invisible testing

class TradingProfile(Enum):
    """Preconfigured hunting grounds"""
    DEFAULT = "default"          # Council-approved baseline
    FTMO = "ftmo"              # Prop firm optimized
    AGGRESSIVE = "aggressive"   # Angela feeling dangerous
    CONSERVATIVE = "conservative"  # Preservation mode

@dataclass
class RiskConfig:
    """Risk parameters - the boundaries of our aggression"""
    mode: RiskMode = RiskMode.FIXED
    
    # Fixed mode parameters
    fixed_pct: Decimal = Decimal("0.006")  # 0.6% default
    
    # Adaptive mode parameters
    adaptive_win_streak_threshold: int = 3
    adaptive_loss_streak_threshold: int = 2
    adaptive_floor_pct: Decimal = Decimal("0.004")  # Never below 0.4%
    adaptive_ceiling_pct: Decimal = Decimal("0.008")  # Never above 0.8%
    
    # Signal strength multipliers
    signal_strength_multipliers: Dict[str, float] = field(default_factory=lambda: {
        "EXTREME": 1.0,      # Full size
        "STRONG": 0.8,       # 80% size
        "MODERATE": 0.6,     # 60% size
        "WEAK": 0.0          # Skip weak signals
    })
    
    # Daily limits (stricter than FTMO)
    daily_soft_dd_pct: Decimal = Decimal("0.038")  # 3.8%
    daily_hard_dd_pct: Decimal = Decimal("0.040")  # 4.0%
    max_total_loss_pct: Decimal = Decimal("0.10")  # 10%
    
    # Position limits
    max_concurrent_positions: int = 3
    max_daily_trades: int = 5
    min_trade_spacing_minutes: int = 30

@dataclass
class CorrelationConfig:
    """Correlation awareness - preventing concentration risk"""
    enabled: bool = True
    
    # DXY filter for USD pairs
    dxy_sr_band_pct: Decimal = Decimal("0.002")  # ±0.2% from S/R
    dxy_enabled: bool = True
    
    # Correlation thresholds
    correlation_window_days: int = 20
    correlation_block_threshold: float = 0.70
    correlation_reduce_threshold: float = 0.50
    
    # Time decay for correlations
    position_decay_hours: int = 4
    decay_factor: float = 0.8  # Reduce correlation weight by 20% after decay_hours
    
    # Cluster definitions
    clusters: Dict[str, List[str]] = field(default_factory=lambda: {
        "USD_MAJORS": ["EURUSD", "GBPUSD", "AUDUSD", "NZDUSD", "USDCHF", "USDCAD"],
        "JPY_CROSSES": ["USDJPY", "EURJPY", "GBPJPY", "AUDJPY"],
        "INDICES": ["US30", "NAS100", "SPX500", "DAX40", "UK100"],
        "METALS": ["XAUUSD", "XAGUSD", "XPTUSD"],
        "CRYPTO": ["BTCUSD", "ETHUSD", "SOLUSD"]
    })

@dataclass
class NewsConfig:
    """News event handling - because the Fed ruins everything"""
    enabled: bool = True
    
    # Blackout windows
    default_blackout_minutes: int = 10
    high_impact_blackout_minutes: int = 15
    rate_decision_blackout_minutes: int = 20
    
    # News fade strategy (trade the reversion)
    fade_strategy_enabled: bool = False
    fade_entry_delay_minutes: int = 45
    fade_window_minutes: int = 30
    
    # Event categories
    tier1_events: List[str] = field(default_factory=lambda: [
        "NFP", "CPI", "FOMC", "ECB", "BOE", "BOJ", "RBA", "RBNZ", "SNB"
    ])
    
    tier2_events: List[str] = field(default_factory=lambda: [
        "GDP", "PMI", "Retail_Sales", "Unemployment", "PPI"
    ])

@dataclass
class StrategyRotationConfig:
    """Strategy performance management - even good strategies have bad days"""
    enabled: bool = True
    
    # Hibernation thresholds
    consecutive_losses_to_hibernate: int = 5
    hibernation_cooldown_hours: int = 48
    
    # Performance tracking
    performance_window_days: int = 20
    min_sharpe_to_remain_active: float = 0.5
    
    # Regime-based adaptation
    regime_adaptation_enabled: bool = True
    regime_detection_window_hours: int = 24
    
    # Strategy weights (can be adjusted dynamically)
    strategy_weights: Dict[str, float] = field(default_factory=lambda: {
        "London_Breakout": 0.33,
        "Volatility_Compression": 0.33,
        "Institutional_Flow": 0.34
    })

@dataclass
class FTMOConfig:
    """FTMO-specific optimizations - because prop firms have rules"""
    enabled: bool = False
    
    # Phase-specific settings
    phase1_target_pct: Decimal = Decimal("0.10")  # 10% profit target
    phase1_days: int = 30
    phase1_aggressive_days: int = 15  # Front-load risk
    
    phase2_target_pct: Decimal = Decimal("0.05")  # 5% profit target
    phase2_days: int = 60
    phase2_max_risk_pct: Decimal = Decimal("0.005")  # Never exceed 0.5% in phase 2
    
    # Time restrictions
    friday_cutoff_gmt: str = "14:00"
    no_weekend_holding: bool = True
    
    # Drawdown limits (FTMO's are 5% daily, 10% max)
    ftmo_daily_limit_pct: Decimal = Decimal("0.05")
    ftmo_max_limit_pct: Decimal = Decimal("0.10")

@dataclass
class AngelaOverrideConfig:
    """Sovereign control parameters - Angela's divine right"""
    enabled: bool = True
    require_signature: bool = True
    
    # Override types allowed
    allow_thesis_trades: bool = True  # "EURUSD will hit 1.1100"
    allow_risk_override: bool = True  # "Use 2% risk today"
    allow_strategy_override: bool = True  # "Only trade London breakouts"
    
    # Signature verification
    public_key_path: str = "keys/angela_sovereign_public.key"
    signature_timeout_seconds: int = 300  # 5 minutes to execute
    
    # Override limits (even Angela has guardrails)
    max_override_risk_pct: Decimal = Decimal("0.02")  # 2% absolute max
    override_respects_daily_dd: bool = True  # Can't override daily loss limits

@dataclass
class SystemConfig:
    """System-wide parameters"""
    # Executor mode
    executor_mode: ExecutorMode = ExecutorMode.DRY_RUN
    
    # Node identification
    node_id: str = "EX-44-PRIMARY"
    cluster_name: str = "WOLFE-PROD"
    
    # High availability
    enable_ha: bool = True
    redis_host: str = "localhost"
    redis_port: int = 6379
    leader_lock_ttl_seconds: int = 30
    leader_heartbeat_seconds: int = 10
    
    # Audit and compliance
    audit_dir: str = "ops/audit"
    enable_immutable_logging: bool = True
    log_rotation_hour_utc: int = 0
    
    # Performance tracking
    enable_attribution: bool = True
    attribution_window_hours: int = 24
    
    # API configuration
    api_rate_limit_per_minute: int = 150
    api_backoff_base_ms: int = 200
    api_backoff_max_ms: int = 5000
    api_max_retries: int = 5

@dataclass
class CopyDecorrConfig:
    """Copy trading decorrelation - making every account unique"""
    enabled: bool = True
    
    # Timing jitter
    delay_min_ms: int = 50
    delay_max_ms: int = 350
    
    # Parameter tilting
    param_tilt_min_pct: Decimal = Decimal("0.03")
    param_tilt_max_pct: Decimal = Decimal("0.07")
    
    # Symbol rotation
    symbol_rotation_enabled: bool = True
    rotation_probability: float = 0.2  # 20% chance to swap correlated symbol
    
    # Firm-wide limits
    max_firm_correlation: float = 0.30
    firm_risk_cap_pct: Decimal = Decimal("0.12")  # 12% max across all accounts

@dataclass
class WolfeConfig:
    """
    The complete v0.4.3 configuration.
    This is where sovereignty meets mathematics.
    """
    # Component configurations
    risk: RiskConfig = field(default_factory=RiskConfig)
    correlation: CorrelationConfig = field(default_factory=CorrelationConfig)
    news: NewsConfig = field(default_factory=NewsConfig)
    strategy_rotation: StrategyRotationConfig = field(default_factory=StrategyRotationConfig)
    ftmo: FTMOConfig = field(default_factory=FTMOConfig)
    angela_override: AngelaOverrideConfig = field(default_factory=AngelaOverrideConfig)
    system: SystemConfig = field(default_factory=SystemConfig)
    copy_decorr: CopyDecorrConfig = field(default_factory=CopyDecorrConfig)
    
    # Profile management
    active_profile: TradingProfile = TradingProfile.DEFAULT
    profile_locked: bool = False  # Prevent accidental profile changes
    
    # Metadata
    version: str = "0.4.3"
    config_hash: Optional[str] = None
    last_modified: Optional[str] = None
    
    def calculate_hash(self) -> str:
        """Calculate configuration hash for audit trail"""
        config_dict = asdict(self)
        config_json = json.dumps(config_dict, sort_keys=True, default=str)
        return hashlib.sha256(config_json.encode()).hexdigest()
    
    def validate(self) -> List[str]:
        """Validate configuration consistency"""
        errors = []
        
        # Risk validations
        if self.risk.daily_hard_dd_pct <= self.risk.daily_soft_dd_pct:
            errors.append("Hard DD must be greater than soft DD")
        
        if self.risk.adaptive_ceiling_pct > self.risk.daily_soft_dd_pct:
            errors.append("Adaptive ceiling cannot exceed daily soft DD")
        
        # FTMO validations
        if self.ftmo.enabled:
            if self.risk.daily_hard_dd_pct > self.ftmo.ftmo_daily_limit_pct:
                errors.append("Our daily DD limit exceeds FTMO's limit")
        
        # Correlation validations
        if self.correlation.correlation_block_threshold <= self.correlation.correlation_reduce_threshold:
            errors.append("Block threshold must be higher than reduce threshold")
        
        # Angela override validations
        if self.angela_override.max_override_risk_pct > self.risk.daily_soft_dd_pct:
            errors.append("Angela's override risk cannot exceed daily soft DD")
        
        return errors
    
    def apply_profile(self, profile: TradingProfile):
        """Apply a predefined trading profile"""
        if self.profile_locked:
            raise ValueError("Profile is locked. Unlock before changing.")
        
        if profile == TradingProfile.FTMO:
            # FTMO optimized settings
            self.ftmo.enabled = True
            self.risk.mode = RiskMode.ADAPTIVE
            self.risk.max_concurrent_positions = 3
            self.risk.max_daily_trades = 5
            self.risk.daily_hard_dd_pct = Decimal("0.045")  # Slightly below FTMO's 5%
            self.news.fade_strategy_enabled = True
            self.strategy_rotation.enabled = True
            
        elif profile == TradingProfile.AGGRESSIVE:
            # Angela feeling dangerous
            self.risk.mode = RiskMode.ADAPTIVE
            self.risk.adaptive_ceiling_pct = Decimal("0.010")  # 1% max
            self.risk.max_concurrent_positions = 5
            self.risk.max_daily_trades = 10
            self.correlation.correlation_block_threshold = 0.80  # Higher tolerance
            
        elif profile == TradingProfile.CONSERVATIVE:
            # Capital preservation mode
            self.risk.mode = RiskMode.FIXED
            self.risk.fixed_pct = Decimal("0.004")  # 0.4% only
            self.risk.max_concurrent_positions = 2
            self.risk.daily_soft_dd_pct = Decimal("0.02")  # 2% soft limit
            self.correlation.correlation_block_threshold = 0.50  # Very strict
            
        self.active_profile = profile
        logger.info(f"Applied profile: {profile.value}")

class ConfigManager:
    """
    Manages configuration loading, validation, and hot-reloading.
    Because configuration is policy, and policy is power.
    """
    
    def __init__(self, config_dir: str = "config"):
        self.config_dir = Path(config_dir)
        self.config_dir.mkdir(exist_ok=True)
        
        self.current_config: Optional[WolfeConfig] = None
        self.config_history: List[str] = []  # Track config changes
        
    def load_config(self, filename: str = "default.yaml") -> WolfeConfig:
        """Load configuration from YAML file"""
        config_path = self.config_dir / filename
        
        if not config_path.exists():
            logger.warning(f"Config file {filename} not found, using defaults")
            return WolfeConfig()
        
        with open(config_path, 'r') as f:
            config_data = yaml.safe_load(f)
        
        # Parse into dataclass structure
        config = self._parse_config_dict(config_data)
        
        # Validate
        errors = config.validate()
        if errors:
            raise ValueError(f"Configuration validation failed: {errors}")
        
        # Calculate hash
        config.config_hash = config.calculate_hash()
        
        # Track in history
        self.config_history.append(config.config_hash)
        
        self.current_config = config
        logger.info(f"Loaded config: {filename} (hash: {config.config_hash[:8]}...)")
        
        return config
    
    def save_config(self, config: WolfeConfig, filename: str = "current.yaml"):
        """Save configuration to YAML file"""
        config_path = self.config_dir / filename
        
        # Convert to dict
        config_dict = asdict(config)
        
        # Add metadata
        import datetime
        config_dict['last_modified'] = datetime.datetime.utcnow().isoformat()
        config_dict['config_hash'] = config.calculate_hash()
        
        with open(config_path, 'w') as f:
            yaml.dump(config_dict, f, default_flow_style=False, sort_keys=False)
        
        logger.info(f"Saved config to {filename}")
    
    def _parse_config_dict(self, data: Dict[str, Any]) -> WolfeConfig:
        """Parse dictionary into WolfeConfig structure"""
        config = WolfeConfig()
        
        # Parse each section
        if 'risk' in data:
            config.risk = self._parse_risk_config(data['risk'])
        
        if 'correlation' in data:
            config.correlation = self._parse_correlation_config(data['correlation'])
        
        if 'news' in data:
            config.news = self._parse_news_config(data['news'])
        
        if 'strategy_rotation' in data:
            config.strategy_rotation = self._parse_strategy_config(data['strategy_rotation'])
        
        if 'ftmo' in data:
            config.ftmo = self._parse_ftmo_config(data['ftmo'])
        
        if 'angela_override' in data:
            config.angela_override = self._parse_angela_config(data['angela_override'])
        
        if 'system' in data:
            config.system = self._parse_system_config(data['system'])
        
        if 'copy_decorr' in data:
            config.copy_decorr = self._parse_decorr_config(data['copy_decorr'])
        
        # Parse profile
        if 'active_profile' in data:
            config.active_profile = TradingProfile(data['active_profile'])
        
        return config
    
    def _parse_risk_config(self, data: Dict) -> RiskConfig:
        """Parse risk configuration section"""
        risk = RiskConfig()
        
        if 'mode' in data:
            risk.mode = RiskMode(data['mode'])
        
        if 'fixed_pct' in data:
            risk.fixed_pct = Decimal(str(data['fixed_pct']))
        
        if 'adaptive' in data:
            adaptive = data['adaptive']
            risk.adaptive_win_streak_threshold = adaptive.get('win_streak_up', 3)
            risk.adaptive_loss_streak_threshold = adaptive.get('loss_streak_down', 2)
            risk.adaptive_floor_pct = Decimal(str(adaptive.get('floor', 0.004)))
            risk.adaptive_ceiling_pct = Decimal(str(adaptive.get('ceiling', 0.008)))
        
        return risk
    
    def _parse_correlation_config(self, data: Dict) -> CorrelationConfig:
        """Parse correlation configuration section"""
        corr = CorrelationConfig()
        corr.enabled = data.get('enabled', True)
        corr.dxy_sr_band_pct = Decimal(str(data.get('dxy_sr_band', 0.002)))
        corr.correlation_window_days = data.get('rolling_window_days', 20)
        corr.position_decay_hours = data.get('decay_hours', 4)
        corr.correlation_block_threshold = data.get('block_threshold', 0.70)
        return corr
    
    def _parse_news_config(self, data: Dict) -> NewsConfig:
        """Parse news configuration section"""
        news = NewsConfig()
        news.enabled = data.get('enabled', True)
        
        if 'tier1_windows' in data:
            news.default_blackout_minutes = data['tier1_windows'].get('default_min', 10)
            news.rate_decision_blackout_minutes = data['tier1_windows'].get('rates_min', 15)
        
        news.fade_strategy_enabled = data.get('fade_strategy', False)
        return news
    
    def _parse_strategy_config(self, data: Dict) -> StrategyRotationConfig:
        """Parse strategy rotation configuration"""
        strat = StrategyRotationConfig()
        strat.enabled = data.get('enabled', True)
        strat.consecutive_losses_to_hibernate = data.get('hibernate_losses', 5)
        strat.hibernation_cooldown_hours = data.get('cooldown_hours', 48)
        strat.regime_adaptation_enabled = data.get('regime_gate', True)
        return strat
    
    def _parse_ftmo_config(self, data: Dict) -> FTMOConfig:
        """Parse FTMO configuration section"""
        ftmo = FTMOConfig()
        ftmo.enabled = data.get('enabled', False)
        ftmo.phase1_target_pct = Decimal(str(data.get('phase1_target_pct', 0.10)))
        ftmo.phase2_max_risk_pct = Decimal(str(data.get('phase2_risk_cap_pct', 0.005)))
        ftmo.friday_cutoff_gmt = data.get('friday_close_gmt', '14:00')
        return ftmo
    
    def _parse_angela_config(self, data: Dict) -> AngelaOverrideConfig:
        """Parse Angela override configuration"""
        angela = AngelaOverrideConfig()
        angela.enabled = data.get('enabled', True)
        angela.require_signature = data.get('required_signature', True)
        return angela
    
    def _parse_system_config(self, data: Dict) -> SystemConfig:
        """Parse system configuration section"""
        sys = SystemConfig()
        
        if 'executor_mode' in data:
            sys.executor_mode = ExecutorMode(data['executor_mode'])
        
        sys.node_id = data.get('node_id', 'EX-44-PRIMARY')
        sys.enable_ha = data.get('enable_ha', True)
        sys.redis_host = data.get('redis_host', 'localhost')
        
        return sys
    
    def _parse_decorr_config(self, data: Dict) -> CopyDecorrConfig:
        """Parse copy decorrelation configuration"""
        decorr = CopyDecorrConfig()
        
        if 'delay_ms' in data:
            decorr.delay_min_ms = data['delay_ms'][0]
            decorr.delay_max_ms = data['delay_ms'][1]
        
        if 'tilt_pct' in data:
            decorr.param_tilt_min_pct = Decimal(str(data['tilt_pct'][0]))
            decorr.param_tilt_max_pct = Decimal(str(data['tilt_pct'][1]))
        
        decorr.symbol_rotation_enabled = data.get('symbol_rotation', True)
        
        return decorr
    
    def hot_reload(self, parameter_path: str, new_value: Any) -> bool:
        """
        Hot-reload a specific parameter without restarting.
        This is where configuration becomes dynamic power.
        """
        if not self.current_config:
            raise ValueError("No config loaded")
        
        # Parse the path (e.g., "risk.fixed_pct")
        parts = parameter_path.split('.')
        
        # Navigate to the parameter
        obj = self.current_config
        for part in parts[:-1]:
            obj = getattr(obj, part)
        
        # Set the new value
        setattr(obj, parts[-1], new_value)
        
        # Validate the change
        errors = self.current_config.validate()
        if errors:
            logger.error(f"Hot reload validation failed: {errors}")
            return False
        
        # Update hash
        self.current_config.config_hash = self.current_config.calculate_hash()
        
        logger.info(f"Hot-reloaded {parameter_path} = {new_value}")
        return True


# Example usage showing the power of configuration
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    # Create config manager
    manager = ConfigManager()
    
    # Create a new configuration
    config = WolfeConfig()
    
    # Apply FTMO profile
    config.apply_profile(TradingProfile.FTMO)
    
    # Customize further
    config.risk.fixed_pct = Decimal("0.007")  # 0.7% risk
    config.angela_override.enabled = True
    config.system.executor_mode = ExecutorMode.HONEYPOT  # Test mode
    
    # Validate
    errors = config.validate()
    if errors:
        print(f"Validation errors: {errors}")
    else:
        print("Configuration valid!")
    
    # Save it
    manager.save_config(config, "ftmo_profile.yaml")
    
    # Display key settings
    print(f"\n{'='*60}")
    print("WOLFEDESK v0.4.3 CONFIGURATION")
    print(f"{'='*60}")
    print(f"Profile: {config.active_profile.value}")
    print(f"Mode: {config.system.executor_mode.value}")
    print(f"Risk Mode: {config.risk.mode.value}")
    print(f"Risk Per Trade: {config.risk.fixed_pct:.2%}")
    print(f"Daily DD Limits: Soft={config.risk.daily_soft_dd_pct:.1%}, Hard={config.risk.daily_hard_dd_pct:.1%}")
    print(f"Max Positions: {config.risk.max_concurrent_positions}")
    print(f"FTMO Mode: {config.ftmo.enabled}")
    print(f"Angela Override: {config.angela_override.enabled}")
    print(f"Correlation Monitoring: {config.correlation.enabled}")
    print(f"Strategy Rotation: {config.strategy_rotation.enabled}")
    print(f"Config Hash: {config.calculate_hash()[:16]}...")
    print(f"{'='*60}")
