# path: scripts/digest.py (panels + attribution; run at 23:30 ET via cron)
from __future__ import annotations

import json
import os
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List

from zoneinfo import ZoneInfo

from config.settings import settings

AUDIT_DIR = Path("ops/audit/logs")
OUT_DIR = Path("ops/audit/digest")
OUT_DIR.mkdir(parents=True, exist_ok=True)


def _iter_events() -> List[Dict]:
    events: List[Dict] = []
    for p in sorted(AUDIT_DIR.glob("*.jsonl")):
        for line in p.read_text().splitlines():
            try:
                events.append(json.loads(line))
            except Exception:
                continue
    # Fallback: try tails
    for p in sorted(AUDIT_DIR.glob("*.jsonl.enc.tail")):
        for line in p.read_text().splitlines():
            try:
                events.append(json.loads(line))
            except Exception:
                continue
    return events


def _panel_counts(evts: List[Dict]) -> str:
    by_evt = Counter(e.get("evt") for e in evts)
    lines = ["### Event Counts"] + [f"- {k}: {v}" for k, v in by_evt.most_common()]
    return "\n".join(lines)


def _panel_corr(evts: List[Dict]) -> str:
    rows = [e.get("payload", {}) for e in evts if e.get("evt") == "CORR_BLOCK"]
    lines = ["### Correlation Blocks"]
    for r in rows[:50]:
        syms = r.get("symbols") or [r.get("symbol_a"), r.get("symbol_b")]
        lines.append(f"- {syms} action={r.get('action')} thr={r.get('threshold')}")
    return "\n".join(lines)


def _panel_ha(evts: List[Dict]) -> str:
    rows = [e for e in evts if (e.get("evt") or "").startswith("HA_")]
    lines = ["### HA Events"] + [f"- {r.get('evt')}: {r.get('payload')}" for r in rows[-20:]]
    return "\n".join(lines)


def _attribution() -> str:
    return (
        f"Node: {settings.NODE_ID}\n"
        f"Mode: {getattr(settings.EXECUTOR_MODE, 'value', str(settings.EXECUTOR_MODE))}\n"
        f"Generated: {datetime.now(ZoneInfo('America/New_York')).isoformat()}\n"
    )


def main() -> int:
    et_now = datetime.now(ZoneInfo("America/New_York"))
    # Note: schedule externally at 23:30 ET. Script itself doesn't sleep.
    evts = _iter_events()
    parts = ["# Wolfe Digest", "", _attribution(), _panel_counts(evts), _panel_corr(evts), _panel_ha(evts)]
    out = "\n\n".join(parts)
    out_path = OUT_DIR / f"digest-{et_now.date().isoformat()}.md"
    out_path.write_text(out)
    print(out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

