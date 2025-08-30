from dataclasses import dataclass

@dataclass
class SymbolStats:
    spread: float
    median_spread: float
    atr_spike: float  # ratio
    slippage_60m_breaches: int

def spread_ok(s: SymbolStats) -> bool:
    return s.spread <= max(1e-9, 1.5 * s.median_spread)

def atr_spike_ok(s: SymbolStats) -> bool:
    return s.atr_spike <= 2.0

def slippage_ok(s: SymbolStats) -> bool:
    return s.slippage_60m_breaches < 3
