# path: config/loader.py
from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict, Iterable

import yaml


DEFAULT_PATH = Path("config/default.yaml")
PROFILE_PATH = Path("config/profile.ftmo.yaml")  # optional


def _read_yaml(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    try:
        return yaml.safe_load(path.read_text()) or {}
    except Exception:
        return {}


def _map_yaml_to_env_keys(doc: Dict[str, Any]) -> Dict[str, Any]:
    """Flatten selected YAML keys to our Settings field names.
    YAML < .env < ENV precedence is handled by pydantic; we just provide base layer.
    """
    out: Dict[str, Any] = {}
    # modes
    mode = (doc.get("modes", {}) or {}).get("executor_mode")
    if mode:
        out["EXECUTOR_MODE"] = str(mode).upper()
    # correlation
    corr = doc.get("correlation", {}) or {}
    if "window_days" in corr:
        out["CORR_WINDOW_DAYS"] = int(corr["window_days"])
    if "block_threshold" in corr:
        out["CORR_BLOCK_THRESHOLD"] = float(corr["block_threshold"])
    if "block_threshold_action" in corr:
        out["CORR_THRESHOLD_ACTION"] = str(corr["block_threshold_action"]).lower()
    if "dxy_band_pct" in corr:
        out["DXY_BAND_PCT"] = float(corr["dxy_band_pct"])
    # gap
    gap = doc.get("gap", {}) or {}
    if "alert_pct" in gap:
        out["GAP_ALERT_PCT"] = float(gap["alert_pct"])
    # features
    feats = doc.get("features", {}) or {}
    if "ha_drills" in feats:
        out["FEATURES_HA_DRILLS"] = bool(feats["ha_drills"])  # noqa: FBT003
    if "ha_status_badge" in feats:
        out["FEATURES_HA_STATUS_BADGE"] = bool(feats["ha_status_badge"])  # noqa: FBT003
    if "auto_flat_all_on_lock_loss" in feats:
        out["FEATURES_AUTO_FLAT_ALL_ON_LOCK_LOSS"] = bool(feats["auto_flat_all_on_lock_loss"])  # noqa: FBT003
    if "auto_register_mt5" in feats:
        out["FEATURES_AUTO_REGISTER_MT5"] = bool(feats["auto_register_mt5"])  # noqa: FBT003
    if "gap_guard" in feats:
        out["FEATURES_GAP_GUARD"] = bool(feats["gap_guard"])  # noqa: FBT003
    # profile settings (optional)
    prof = (doc.get("profile") or "").strip().lower()
    if prof:
        out["PROFILE"] = prof
    return out


def yaml_settings_source() -> Dict[str, Any]:
    """Load YAMLs and map to Settings fields. default.yaml + optional profile overrides.
    default < profile (if present)
    """
    base = _map_yaml_to_env_keys(_read_yaml(DEFAULT_PATH))
    prof_doc = _read_yaml(PROFILE_PATH)
    profile = _map_yaml_to_env_keys(prof_doc) if prof_doc else {}
    base.update(profile)
    return base


# path: config/settings.py (add YAML source + GAP + flag)
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

    # Identity / Mode
    NODE_ID: str = "EX-44-PRIMARY"
    EXECUTOR_MODE: ExecutorMode = ExecutorMode.DRY_RUN

    @field_validator("EXECUTOR_MODE", mode="before")
    @classmethod
    def _alias_modes(cls, v: str | ExecutorMode):
        if isinstance(v, str) and v.upper() in {"HONEYPOT", "PAPER"}:
            return ExecutorMode.SHADOW
        return v

    # Environment
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

    # Correlation controls
    CORR_WINDOW_DAYS: int = 20
    CORR_BLOCK_THRESHOLD: float = 0.70
    CORR_THRESHOLD_ACTION: Literal["block", "halve"] = "block"
    DXY_BAND_PCT: float = 0.002

    # Gap/Corp-action guard
    GAP_ALERT_PCT: float = 0.15

    # Dashboard
    DASH_PORT: int = 9090
    DASH_TOKEN: str = "change-me"

    # Features (safe/off by default)
    FEATURES_HA_DRILLS: bool = False
    FEATURES_AUTO_FLAT_ALL_ON_LOCK_LOSS: bool = False
    FEATURES_HA_STATUS_BADGE: bool = True
    FEATURES_AUTO_REGISTER_MT5: bool = False
    FEATURES_GAP_GUARD: bool = False

    @property
    def REDIS_URL_EFFECTIVE(self) -> str:
        if self.REDIS_URL:
            return self.REDIS_URL
        return f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}/0"

    # YAML source precedence: YAML < .env < ENV
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

