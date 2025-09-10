# path: core/executor/loop.py
from __future__ import annotations

import logging
from typing import Dict, List, Optional, Any

from config.settings import Settings
from core.executor.register import get_strategy_class, register_strategy
from strategies.pilot_sma import PilotSMAStrategy, Tick

logger = logging.getLogger(__name__)

# Global strategy instances
_STRATEGIES: Dict[str, Any] = {}


def load_strategies(settings: Optional[Settings] = None) -> None:
    """Load enabled strategies from configuration."""
    settings = settings or Settings()
    
    # Register available strategy classes
    register_strategy("pilot_sma", PilotSMAStrategy)
    
    # Check if strategy pilot feature is enabled
    if not getattr(settings.features, 'strategy_pilot', False):
        logger.info("Strategy pilot feature is disabled")
        return
    
    # Get list of enabled strategies
    enabled_strategies = []
    if hasattr(settings, 'strategies') and hasattr(settings.strategies, 'enabled'):
        enabled_strategies = settings.strategies.enabled
    
    if not enabled_strategies:
        logger.info("No strategies enabled in configuration")
        return
    
    # Instantiate enabled strategies
    for strategy_name in enabled_strategies:
        if strategy_name in _STRATEGIES:
            logger.debug(f"Strategy {strategy_name} already loaded")
            continue
        
        strategy_class = get_strategy_class(strategy_name)
        if strategy_class:
            try:
                strategy_instance = strategy_class(settings=settings)
                _STRATEGIES[strategy_name] = strategy_instance
                logger.info(f"Loaded strategy: {strategy_name}")
            except Exception as e:
                logger.error(f"Failed to load strategy {strategy_name}: {e}", exc_info=True)
        else:
            logger.warning(f"Strategy class not found: {strategy_name}")
    
    logger.info(f"Strategy loading complete: {len(_STRATEGIES)} strategies active")


def process_tick(tick: Tick) -> None:
    """Process tick through all active strategies."""
    for name, strategy in _STRATEGIES.items():
        try:
            if hasattr(strategy, 'on_tick'):
                strategy.on_tick(tick)
        except Exception as e:
            logger.error(f"Error processing tick in strategy {name}: {e}", exc_info=True)


def get_strategy_status() -> List[Dict[str, Any]]:
    """Get status of all active strategies."""
    status_list = []
    for name, strategy in _STRATEGIES.items():
        try:
            if hasattr(strategy, 'get_status'):
                status = strategy.get_status()
            else:
                status = {"strategy": name, "enabled": True}
            status_list.append(status)
        except Exception as e:
            logger.error(f"Error getting status for strategy {name}: {e}")
            status_list.append({"strategy": name, "error": str(e)})
    
    return status_list


def stop_strategies() -> None:
    """Stop all active strategies."""
    for name, strategy in _STRATEGIES.items():
        try:
            if hasattr(strategy, 'stop'):
                strategy.stop()
                logger.info(f"Stopped strategy: {name}")
        except Exception as e:
            logger.error(f"Error stopping strategy {name}: {e}", exc_info=True)
    
    _STRATEGIES.clear()
    logger.info("All strategies stopped")


def get_strategy(name: str) -> Optional[Any]:
    """Get a specific strategy instance."""
    return _STRATEGIES.get(name)