# path: config/settings.py
from __future__ import annotations

from enum import Enum
from typing import Any, Literal, Tuple, Union, Annotated

from pydantic import Field, field_validator, ValidationError
from pydantic_settings import (
    BaseSettings,
    PydanticBaseSettingsSource,
    SettingsConfigDict,
)

from .loader import yaml_settings_source
from .models import Adapters, Broker, BrokerMT5, Executor, Features, Safety, Strategies


class ExecutorMode(str, Enum):
    DRY_RUN = "DRY_RUN"
    SHADOW = "SHADOW"
    LIVE = "LIVE"


class _YamlMirrorSource(PydanticBaseSettingsSource):
    """pydantic-settings v2 settings source that feeds values from YAML.

    Lowest precedence; allows ENV and .env to override.
    Implements both `__call__` and `get_field_value` as required by v2.
    """

    def __init__(self, settings_cls: type[BaseSettings]):
        super().__init__(settings_cls)
        self._data: dict[str, Any] = yaml_settings_source()

    def __call__(self) -> dict[str, Any]:
        # Return a mapping of field_name → value
        return self._data

    def get_field_value(
        self,
        field,  # pydantic.fields.FieldInfo
        field_name: str,
    ) -> tuple[Any, str | None, dict[str, Any] | None]:
        if field_name in self._data:
            return self._data[field_name], field_name, self._data
        return None, None, None


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore",
        case_sensitive=False,
        env_nested_delimiter="__",
        nested_model_default_partial_update=True,
    )

    NODE_ID: str = "EX-44-PRIMARY"
    EXECUTOR_MODE: ExecutorMode = ExecutorMode.LIVE

    @field_validator("EXECUTOR_MODE", mode="before")
    @classmethod
    def _alias_modes(cls, v: str | ExecutorMode):
        if isinstance(v, str) and v.upper() in {"HONEYPOT", "PAPER"}:
            return ExecutorMode.SHADOW
        return v

    ENV: Literal["dev", "test", "prod"] = "dev"

    # Redis / HA
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_URL: str | None = None
    HA_LOCK_KEY: str = "wolfe:ha:lock"

    LOCK_TTL_MS: int = 3000
    HEARTBEAT_MS: int = 1000

    # Backoff
    BACKOFF_BASE_MS: int = 100
    BACKOFF_MAX_MS: int = 5000
    BACKOFF_JITTER_MS: int = 200
    BACKOFF_RETRIES: int = 5

    # Nuclear
    PRAGUE_TZ: str = "Europe/Prague"
    NUCLEAR_PUBKEY: str = ""

    # Risk & caps
    DAILY_HARD_DD_PCT: float = 0.04
    DAILY_SOFT_FREEZE_PCT: float = 0.038
    ORDER_RATE_CAP_PER_60S: int = 150

    COPY_JITTER_MS: Tuple[int, int] = (50, 350)
    COPY_TILT_PCT: Tuple[float, float] = (0.03, 0.07)
    CLUSTER_CAP_MULT: float = 1.25

    RISK_RATCHET_HALF_AFTER_RED_DAYS: int = 2

    # Adaptive Risk
    RISK_MODE: Literal["ratchet", "adaptive", "both"] = "ratchet"
    RISK_FLOOR_PCT: float = 0.25
    RISK_CEILING_PCT: float = 1.50

    # Correlation controls
    CORR_WINDOW_DAYS: int = 20
    CORR_BLOCK_THRESHOLD: float = 0.70
    CORR_THRESHOLD_ACTION: Literal["block", "halve"] = "block"
    DXY_BAND_PCT: float = 0.002

    # Gap/Corp-action
    GAP_ALERT_PCT: float = 0.15

    # Dashboard
    DASH_PORT: int = 9090
    DASH_TOKEN: str = "change-me"

    # Features (flat env mirrors)
    FEATURES_HA_DRILLS: bool = False
    FEATURES_AUTO_FLAT_ALL_ON_LOCK_LOSS: bool = False
    FEATURES_HA_STATUS_BADGE: bool = True
    FEATURES_AUTO_REGISTER_MT5: bool = False
    FEATURES_GAP_GUARD: bool = False
    FEATURES_RISK_ADAPTER: bool = False
    FEATURES_STRATEGY_PILOT: bool = False

    # Nested app config (from YAML; overridable via env)
    broker: Broker = Field(default_factory=lambda: Broker(mt5=BrokerMT5(server="", login="", password="")))
    adapters: Adapters = Field(default_factory=Adapters)
    watchlist: list[str] = Field(default_factory=list, json_schema_extra={"format": "comma-separated"})
    executor: Executor = Field(default_factory=Executor)
    safety: Safety = Field(default_factory=Safety)
    features: Features = Field(default_factory=Features)
    strategies: Strategies = Field(default_factory=Strategies)

    @field_validator("watchlist", mode="before")
    @classmethod
    def _parse_watchlist(cls, v):
        """Parse watchlist from various sources (YAML list, env string, etc.)"""
        # Handle None or empty cases first
        if v is None or v == "":
            return []
        
        if isinstance(v, list):
            return v
        
        if isinstance(v, str):
            # Handle empty string case - this prevents the JSON parsing error
            if not v.strip():
                return []
            
            # Special handling for common empty cases that might cause JSON errors
            if v.strip() in ('""', "''", '[]', '{}'):
                return []
            
            # Try to parse as JSON first (for pydantic-settings compatibility)
            try:
                import json
                result = json.loads(v)
                if isinstance(result, list):
                    return result
                # If it's not a list, treat as single item
                return [str(result)]
            except (json.JSONDecodeError, TypeError, ValueError):
                # Fall back to comma-separated string parsing
                return [item.strip() for item in v.split(",") if item.strip()]
        
        # Handle any other type by returning empty list
        return []

    @property
    def REDIS_URL_EFFECTIVE(self) -> str:
        if self.REDIS_URL:
            return self.REDIS_URL
        return f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}/0"

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        # Priority high→low: init > ENV > .env > secrets > YAML
        return (
            init_settings,
            env_settings,
            dotenv_settings,
            file_secret_settings,
            _YamlMirrorSource(settings_cls),
        )


try:
    settings = Settings()
except Exception as e:
    if "watchlist" in str(e) and "JSONDecodeError" in str(e):
        # Handle the watchlist JSON parsing error by setting a default value
        import os
        os.environ.setdefault("WATCHLIST", "[]")
        settings = Settings()
    else:
        raise
