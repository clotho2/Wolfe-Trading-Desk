# path: CHECKLIST_DONE.md
# Wolfe Trading Desk — v0.4.3 Checklist (Commits 02–15)

**Status:** ✅ Code staged in this branch as full-file replacements.

## Commits
- **Commit 02:** Mode aliasing (HONEYPOT→SHADOW), correlation enforcement (20D), DXY band, dashboard watermark.
- **Commit 03:** HA leader (Redis, TTL=3000ms, HB=1000ms, fencing), split-brain lockdown, `/ha/status` + `/ha/ack`, HA chip; auto flat-all (flag), debounce, adapter registry.
- **Commit 04:** Nuclear lock (Ed25519 day nonce @ Prague), `/nuclear/re-enable`, `NUCLEAR_LOCKED/RESUMED` events.
- **Commit 05:** Correlation controls in ComplianceGuard, acceptance tests, `scripts/dev_run.py`.
- **Commit 06:** Gap/Corp-Action Guard @15%, YAML loader + files, tests.
- **Commit 07:** Adaptive Risk Adapter + YAML mirrors, sample_returns + loader, wiring into sizing (flag), integration tests.
- **Commit 08:** Partial fills policy + `PARTIAL_FILL` events, tests.
- **Commit 09:** FTMO per-account profile helpers (cutoff + risk cap), tests.
- **Commit 10:** Digest @ 23:30 ET with attribution + panels.
- **Commit 11:** cTrader/DXtrade adapters (stubs + parity replay).
- **Commit 12:** Backoff helper with deterministic jitter + tests.
- **Commit 13:** Reason code schema guard + tests.
- **Commit 14:** Pytest config + GitHub Actions CI with coverage gate (≥85% for changed files).
- **Commit 15:** This checklist.
- ## Fix Pass — Commits 16–24
- **16**: Redis HA leader with fencing, ack gating, split-brain auto-flat (flag, 5s cooldown) + tests (fakeredis)
- **17**: SHADOW semantics across adapters; watermark middleware; tests
- **18**: Nuclear engage endpoint + Ed25519 re-enable flow; tests
- **19**: GitHub Actions CI workflow (ruff, black, pytest, coverage gate)
- **20**: PR body draft + spec diff tool
- **21**: on_loss cooldown duplication guard + test
- **22**: Config precedence (YAML < .env < ENV) + .env.example + tests
- **23**: Health endpoint + dashboard badge polish
- **24**: EX-44 deployment notes

## Files added/changed (highlights)
- `config/loader.py`, `config/settings.py`, `config/default.yaml`, `config/profile.ftmo.yaml`
- `engine/ComplianceGuard/core.py`, `engine/CopyDeCorr/core.py`, `engine/execution/partial_fills.py`
- `engine/risk.py`, `risk/adapters/risk_adapter.py`, `tests/risk/test_risk_adapter.py`
- `ops/ha/*`, `infra/ha/*`, `server/api/nuclear.py`, `security/*`, `shared/state/*`, `shared/events/*`, `shared/utils/backoff.py`
- `adapters/mt5/*`, `adapters/ctrader/adapter.py`, `adapters/dxtrade/adapter.py`
- `scripts/dev_run.py`, `scripts/digest.py`
- `tests/*` (acceptance, drills, integration)
- `pytest.ini`, `ci/github-actions.yml`, `.ci/coverage_gate.py`

## TODOs (tracked via tools/spec_diff.py — placeholder)
- Flesh MT5 adapter with full broker bindings where stubs remain.
- Add DXtrade/cTrader parity replay datasets in `ops/parity/`.
- Expand dashboard panels for digest preview and live event stream.
- Wire FTMO profile into account selection and order gating flow.
- Extend ComplianceGuard with slippage SLO windowing tests.
