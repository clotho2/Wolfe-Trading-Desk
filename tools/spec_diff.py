# path: tools/spec_diff.py
# (same as earlier commit; retained here for completeness)
"""
Spec diff helper (0.4.2 → 0.4.3).
Usage:
  python tools/spec_diff.py --from specs/v0_4_2.md --to specs/v0_4_3_delta.md
Outputs Markdown; exit 0 always.
"""
from __future__ import annotations
import argparse
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import List

@dataclass
class Row:
    section: str
    delta: str
    files: str
    tests: str
    status: str

KEYS = {
    "HA / Leader": ["TTL", "fencing", "split_brain", "leader", "heartbeat"],
    "Modes": ["SHADOW", "HONEYPOT"],
    "Gap Guard": ["gap", "15%"],
    "Backoff": ["backoff", "100ms", "5000"],
    "Partial Fills": ["partial", "60%", "spread"],
    "Nuclear": ["Ed25519", "Prague", "nonce", "re-enable"],
    "Adaptive Risk": ["adaptive", "ratchet", "both"],
    "Correlation": ["20D", "0.70", "DXY"],
    "FTMO Profile": ["FTMO", "Friday", "phase"],
    "Dashboard/Digest": ["badge", "digest", "23:30"],
    "Adapters": ["cTrader", "DXtrade", "MT5"],
    "Events Bus": ["reason", "schema", "emit"],
    "Flags/Migrations": ["flag", "default", "OFF", "0.4.3"],
}

DELTA = {
    "HA / Leader": "TTL=3s, fencing, SPLIT_BRAIN",
    "Modes": "SHADOW + alias HONEYPOT",
    "Gap Guard": "15% halt",
    "Backoff": "100→5000ms +±200ms",
    "Partial Fills": "enum + 60% branch",
    "Nuclear": "Ed25519, Prague nonce, endpoint",
    "Adaptive Risk": "modes + reason",
    "Correlation": "20D, 0.70, DXY band",
    "FTMO Profile": "pacing, per-trade cap, Friday cutoff",
    "Dashboard/Digest": "badge, nightly digest",
    "Adapters": "MT5 + stubs for cTrader/DXtrade",
    "Events Bus": "schema/emit",
    "Flags/Migrations": "default OFF, 042→043",
}

FILES = {
    "HA / Leader": "infra/ha/*",
    "Modes": "core/executor/*, gateway/http/*",
    "Gap Guard": "engine/ComplianceGuard/core.py",
    "Backoff": "shared/utils/backoff.py",
    "Partial Fills": "engine/execution/partial_fills.py",
    "Nuclear": "security/nuclear.py, server/api/nuclear.py",
    "Adaptive Risk": "risk/adapters/risk_adapter.py, engine/risk.py",
    "Correlation": "engine/CopyDeCorr/core.py, engine/ComplianceGuard/core.py",
    "FTMO Profile": "engine/profiles/ftmo.py",
    "Dashboard/Digest": "ops/dashboard/app.py, scripts/digest.py",
    "Adapters": "adapters/*",
    "Events Bus": "shared/events/schema.py, shared/events/bus.py",
    "Flags/Migrations": "config/*, migrations/*",
}

TESTS = {
    "HA / Leader": "tests/ha/test_leader_redis.py",
    "Modes": "tests/mode/*",
    "Gap Guard": "tests/acceptance/test_gap_guard.py",
    "Backoff": "tests/utils/test_backoff.py",
    "Partial Fills": "tests/execution/test_partial_fills.py",
    "Nuclear": "tests/security/test_nuclear_backend.py",
    "Adaptive Risk": "tests/risk/test_risk_adapter.py, tests/integration/test_sizing_with_adapter.py",
    "Correlation": "tests/acceptance/test_correlation_controls.py",
    "FTMO Profile": "tests/profiles/test_ftmo.py",
    "Dashboard/Digest": "tests/ops/test_digest.py",
    "Adapters": "tests/adapters/*",
    "Events Bus": "tests/events/test_event_schema.py",
    "Flags/Migrations": "tests/config/*",
}


def has_all(text: str, needles: List[str]) -> bool:
    t = text.lower()
    return all(n.lower() in t for n in needles)


def render(src: str, dst: str) -> str:
    out = ["## Spec Diff (0.4.2 → 0.4.3)", "| Section | Delta | Files | Tests | Status |", "|---|---|---|---|---|"]
    for section, needles in KEYS.items():
        status = "✅" if has_all(dst, needles) else ("⚠️" if any(n.lower() in dst.lower() for n in needles) else "⬜")
        out.append(f"| {section} | {DELTA.get(section,'')} | {FILES.get(section,'')} | {TESTS.get(section,'')} | {status} |")
    return "\n".join(out)


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--from", dest="src", required=True)
    ap.add_argument("--to", dest="dst", required=True)
    a = ap.parse_args(argv)
    try:
        src = Path(a.src).read_text(encoding="utf-8", errors="ignore")
    except Exception:
        src = ""
    try:
        dst = Path(a.dst).read_text(encoding="utf-8", errors="ignore")
    except Exception:
        dst = ""
    print(render(src, dst))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
