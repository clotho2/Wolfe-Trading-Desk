# path: config/settings.py (add FTMO fields)
from __future__ import annotations
from enum import Enum
from typing import Tuple, Literal, Callable, Any

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from .loader import yaml_settings_source


class ExecutorMode(str, Enum):
    DRY_RUN = "DRY_RUN"
    SHADOW = "SHADOW"
    LIVE = "LIVE"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore", case_sensitive=False)

    NODE_ID: str = "EX-44-PRIMARY"
    EXECUTOR_MODE: ExecutorMode = ExecutorMode.DRY_RUN

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

    RISK_MODE: Literal["ratchet", "adaptive", "both"] = "ratchet"
    RISK_FLOOR_PCT: float = 0.25
    RISK_CEILING_PCT: float = 1.50

    CORR_WINDOW_DAYS: int = 20
    CORR_BLOCK_THRESHOLD: float = 0.70
    CORR_THRESHOLD_ACTION: Literal["block", "halve"] = "block"
    DXY_BAND_PCT: float = 0.002

    GAP_ALERT_PCT: float = 0.15

    # FTMO profile mirrors
    FTMO_PHASE1_PACING_BONUS_PCT: float = 7.0
    FTMO_PHASE2_MAX_PER_TRADE_RISK_PCT: float = 0.5
    FTMO_FRIDAY_CUTOFF_GMT: str = "14:00"

    # Dashboard
    DASH_PORT: int = 9090
    DASH_TOKEN: str = "change-me"

    # Features
    FEATURES_HA_DRILLS: bool = False
    FEATURES_AUTO_FLAT_ALL_ON_LOCK_LOSS: bool = False
    FEATURES_HA_STATUS_BADGE: bool = True
    FEATURES_AUTO_REGISTER_MT5: bool = False
    FEATURES_GAP_GUARD: bool = False
    FEATURES_RISK_ADAPTER: bool = False

    @property
    def REDIS_URL_EFFECTIVE(self) -> str:
        if self.REDIS_URL:
            return self.REDIS_URL
        return f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}/0"

    @classmethod
    def settings_customise_sources(
        cls,
        init_settings: Callable[..., Any],
        env_settings: Callable[..., Any],
        dotenv_settings: Callable[..., Any],
        file_secret_settings: Callable[..., Any],
    ):
        return (lambda: yaml_settings_source(), dotenv_settings, env_settings, init_settings, file_secret_settings)


settings = Settings()
