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
