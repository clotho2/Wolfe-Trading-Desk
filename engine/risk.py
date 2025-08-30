from dataclasses import dataclass
from config.settings import settings

@dataclass
class RiskParams:
    atr: float
    account_equity: float
    single_trade_risk_pct: float

def atr_normalized_size(params: RiskParams) -> float:
    # Simple placeholder: equity * risk% / (ATR * scale)
    scale = max(params.atr, 1e-6)
    return (params.account_equity * params.single_trade_risk_pct) / scale

def cluster_cap(max_single_trade_risk: float) -> float:
    return max_single_trade_risk * settings.CLUSTER_CAP_MULT
