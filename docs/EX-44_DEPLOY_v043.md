# path: docs/EX-44_DEPLOY_v043.md
# EX-44 — Deployment Notes (v0.4.3)

## Safe boot recipe
- `EXECUTOR_MODE=SHADOW`
- `SAFETY_NO_LIVE=1`
- `features.auto_flat_all_on_lock_loss=false`
- `features.risk_adapter=false`
- `NUCLEAR_PUBKEY` set (re-enable UI off)

## Smoke checklist
```bash
python -m compileall -q .
python scripts/dev_run.py --mode SHADOW --badge
# Open dashboard root → HA badge visible ("HA OFF" OK if Redis missing)
# POST /nuclear/engage (SHADOW): verify audit events; no broker I/O
```

## Systemd sample (optional)
- Service files for uvicorn can be provided; keep SHADOW defaults in env.

