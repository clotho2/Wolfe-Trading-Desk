# path: tests/utils/returns_loader.py
from __future__ import annotations

import csv
from pathlib import Path
from typing import List


def load_sample_returns(path: Path | None = None) -> List[float]:
    p = path or Path("data/sample_returns.csv")
    out: List[float] = []
    with p.open("r", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            try:
                out.append(float(row["pct_change"]))
            except Exception:
                continue
    return out

