import random, time, json
from dataclasses import dataclass, asdict
from typing import List, Dict, Any
from config.settings import settings

@dataclass
class DecorRecord:
    account_id: str
    strategy_fingerprint: str
    jitter_ms: int
    tilt: Dict[str, float]
    symbol_mask: List[str]

def apply_decorrelation(account_id: str, strategy_fingerprint: str, symbols: List[str]) -> DecorRecord:
    jitter_ms = random.randint(*settings.COPY_JITTER_MS)
    tilt_val = random.uniform(*settings.COPY_TILT_PCT)
    mask = symbols[:]  # placeholder rotation
    rec = DecorRecord(
        account_id=account_id,
        strategy_fingerprint=strategy_fingerprint,
        jitter_ms=jitter_ms,
        tilt={"ema_fast": round(tilt_val, 4)},
        symbol_mask=mask,
    )
    return rec
