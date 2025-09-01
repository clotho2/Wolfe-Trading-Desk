# config/settings.py
from __future__ import annotations
from enum import Enum
from typing import Tuple, Literal

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class ExecutorMode(str, Enum):
    DRY_RUN = "DRY_RUN"
    SHADOW = "SHADOW"  # a.k.a. HONEYPOT
    LIVE = "LIVE"


class Settings(BaseSettings):
    """Pydantic v2 Settings.
    - Reads from .env by default
    - Ignores unknown keys (forward compatibility)
    - Provides Council v0.4.3 config surface (defaults keep new features OFF)
    """

    # v2 config: read .env and IGNORE unknown keys
    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore",
        case_sensitive=False,
    )

    # ---------------------------- Identity / Mode ----------------------------
    NODE_ID: str = "EX-44-PRIMARY"
    EXECUTOR_MODE: ExecutorMode = ExecutorMode.DRY_RUN

    @field_validator("EXECUTOR_MODE", mode="before")
    @classmethod
    def _alias_modes(cls, v: str | ExecutorMode):
        # Back-compat: map PAPER/HONEYPOT → SHADOW (Council naming)
        if isinstance(v, str):
            up = v.upper()
            if up in {"HONEYPOT", "PAPER"}:
                return ExecutorMode.SHADOW
        return v

    # ------------------------------- Leader/HA -------------------------------
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    LOCK_TTL_MS: int = 3000  # leader lock TTL
    HEARTBEAT_MS: int = 1000  # leader heartbeat interval

    # -------------------------------- Backoff --------------------------------
    BACKOFF_BASE_MS: int = 100
    BACKOFF_MAX_MS: int = 5000
    BACKOFF_JITTER_MS: int = 200
    BACKOFF_RETRIES: int = 5

    # --------------------------------- Nuclear --------------------------------
    PRAGUE_TZ: str = "Europe/Prague"
    NUCLEAR_PUBKEY: str = ""  # base64 raw 32-byte Ed25519 public key

    # ------------------------------- Risk & Caps ------------------------------
    DAILY_HARD_DD_PCT: float = 0.04
    DAILY_SOFT_FREEZE_PCT: float = 0.038
    ORDER_RATE_CAP_PER_60S: int = 150

    # Copy / decorrelation (legacy jitter/tilt)
    COPY_JITTER_MS: Tuple[int, int] = (50, 350)
    COPY_TILT_PCT: Tuple[float, float] = (0.03, 0.07)

    # Cluster cap (v0.4.2)
    CLUSTER_CAP_MULT: float = 1.25

    # Adaptive risk (default off; wired later)
    RISK_RATCHET_HALF_AFTER_RED_DAYS: int = 2

    # Correlation controls (v0.4.3)
    CORR_BLOCK_THRESHOLD: float = 0.70
    CORR_THRESHOLD_ACTION: Literal["block", "halve"] = "block"
    DXY_BAND_BPS: int = 20  # ±0.20% support/resistance band for USD pairs

    # ------------------------------- Dashboard -------------------------------
    DASH_PORT: int = 9090
    DASH_TOKEN: str = "change-me"


settings = Settings()
