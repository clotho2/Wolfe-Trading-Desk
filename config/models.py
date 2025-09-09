# path: config/models.py
from __future__ import annotations

from typing import List, Literal

from pydantic import BaseModel, field_validator


class BrokerMT5(BaseModel):
    server: str
    login: str
    password: str

    @field_validator("login", mode="before")
    @classmethod
    def _convert_login_to_string(cls, v):
        """Convert login to string if it's an integer"""
        return str(v) if v is not None else ""


class Broker(BaseModel):
    provider: Literal["mt5"] = "mt5"
    mt5: BrokerMT5


class Adapters(BaseModel):
    mt5: dict = {"enabled": True}


class Executor(BaseModel):
    mode: Literal["LIVE", "DRY_RUN", "SHADOW"] = "SHADOW"


class Safety(BaseModel):
    no_live: bool = True


class Features(BaseModel):
    auto_flat_all_on_lock_loss: bool = False
    risk_adapter: bool = False
    ha_status_badge: bool = True
    gap_guard: bool = True


class AppConfig(BaseModel):
    broker: Broker
    adapters: Adapters = Adapters()
    watchlist: List[str] = []
    executor: Executor = Executor()
    safety: Safety = Safety()
    features: Features = Features()
