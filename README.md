# WolfeDesk Trading System v0.4.3 — Spec-Locked Scaffold

This repository template matches the Council v0.4.2→v0.4.3 spec: exact folder tree, config, Prague clock + DST tests,
immutable audit chain (SHA-256 + AES-GCM) w/ UTC midnight rotation + validator, FastAPI dashboard w/ token auth + two-step **KILL ALL**.

## Quickstart

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # edit as needed (EXECUTOR_MODE=DRY_RUN)
make test
make run-dry
```

Open http://localhost:9090 (LAN only recommended). Supply `Authorization: Bearer <DASH_TOKEN>` for protected endpoints.

## Structure (must match spec)

- adapters/{mt5,ctrader,dxtrade}
- engine/{ComplianceGuard,StrategyTester,CopyDeCorr, risk.py, filters.py, timebox.py}
- ops/dashboard/app.py (FastAPI) + ops/audit/* (immutable log chain + validator)
- config/settings.py (Pydantic Settings, `.env` driven)
- scripts/digest.py (nightly council digest)
- tests/{unit,integration,replay_parity}

## Modes

- DRY_RUN (48h mandatory burn-in) → PAPER (20 sessions) → LIVE (only after acceptance gates pass)
