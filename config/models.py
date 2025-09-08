# path: config/models.py
from __future__ import annotations

from typing import List, Literal

from pydantic import BaseModel


class BrokerMT5(BaseModel):
    server: str
    login: str
    password: str


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
