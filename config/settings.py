from pydantic_settings import BaseSettings
from enum import Enum
from typing import Tuple

class ExecutorMode(str, Enum):
    DRY_RUN = "DRY_RUN"
    PAPER = "PAPER"
    LIVE = "LIVE"

class Settings(BaseSettings):
    EXECUTOR_MODE: ExecutorMode = ExecutorMode.DRY_RUN
    PRAGUE_TZ: str = "Europe/Prague"
    DAILY_HARD_DD_PCT: float = 0.04
    DAILY_SOFT_FREEZE_PCT: float = 0.038
    NEWS_TIER1_WINDOW_MIN: int = 10
    ORDER_RATE_CAP_PER_60S: int = 150
    COPY_JITTER_MS: Tuple[int, int] = (50, 350)
    COPY_TILT_PCT: Tuple[float, float] = (0.03, 0.07)
    CLUSTER_CAP_MULT: float = 1.25
    RISK_RATCHET_HALF_AFTER_RED_DAYS: int = 2
    DASH_PORT: int = 9090
    DASH_TOKEN: str = "change-me"
    class Config:
        env_file = ".env"

settings = Settings()
