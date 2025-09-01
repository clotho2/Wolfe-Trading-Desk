# path: config/settings.py (Correlation keys extended)
from __future__ import annotations
from enum import Enum
from typing import Tuple, Literal

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class ExecutorMode(str, Enum):
    DRY_RUN = "DRY_RUN"
    SHADOW = "SHADOW"
    LIVE = "LIVE"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore", case_sensitive=False)

    # Identity / Mode
    NODE_ID: str = "EX-44-PRIMARY"
    EXECUTOR_MODE: ExecutorMode = ExecutorMode.DRY_RUN

    @field_validator("EXECUTOR_MODE", mode="before")
    @classmethod
    def _alias_modes(cls, v: str | ExecutorMode):
        if isinstance(v, str) and v.upper() in {"HONEYPOT", "PAPER"}:
            return ExecutorMode.SHADOW
        return v

    # Environment gate for dev helpers
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
    NUCLEAR_PUBKEY: str = ""  # base64 raw 32 bytes

    # Risk & caps
    DAILY_HARD_DD_PCT: float = 0.04
    DAILY_SOFT_FREEZE_PCT: float = 0.038
    ORDER_RATE_CAP_PER_60S: int = 150

    COPY_JITTER_MS: Tuple[int, int] = (50, 350)
    COPY_TILT_PCT: Tuple[float, float] = (0.03, 0.07)
    CLUSTER_CAP_MULT: float = 1.25

    RISK_RATCHET_HALF_AFTER_RED_DAYS: int = 2

    # Correlation controls (v0.4.3)
    CORR_WINDOW_DAYS: int = 20
    CORR_BLOCK_THRESHOLD: float = 0.70
    CORR_THRESHOLD_ACTION: Literal["block", "halve"] = "block"
    DXY_BAND_PCT: float = 0.002  # ±0.20%; applies to USD pairs cluster regime

    # Dashboard
    DASH_PORT: int = 9090
    DASH_TOKEN: str = "change-me"

    # Features (safe/off by default)
    FEATURES_HA_DRILLS: bool = False
    FEATURES_AUTO_FLAT_ALL_ON_LOCK_LOSS: bool = False
    FEATURES_HA_STATUS_BADGE: bool = True
    FEATURES_AUTO_REGISTER_MT5: bool = False

    @property
    def REDIS_URL_EFFECTIVE(self) -> str:
        if self.REDIS_URL:
            return self.REDIS_URL
        return f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}/0"


settings = Settings()
