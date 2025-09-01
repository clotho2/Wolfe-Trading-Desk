# path: engine/risk.py (integrate RiskAdapter feature-gated sizing flow)
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Optional, Tuple

from config.settings import settings
from ops.audit.immutable_audit import append_event
from risk.adapters.risk_adapter import RiskAdapter, RiskConfig

