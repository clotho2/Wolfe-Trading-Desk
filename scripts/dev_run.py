# path: scripts/dev_run.py
"""WolfeDesk dev launcher (safe defaults).

Examples:
  python scripts/dev_run.py --mode SHADOW --ha --badge --auto-flat
  python scripts/dev_run.py --mode LIVE --i-know-what-im-doing

Flags:
  --mode {SHADOW,DRY_RUN,LIVE}  Default SHADOW
  --ha                         Enable HA bootstrap
  --badge                      Show HA status badge on / (default on)
  --auto-flat                  Auto flat-all on lock loss (feature flag)
  --port 8000                  Uvicorn port
  --i-know-what-im-doing       Allow LIVE without SAFETY_NO_LIVE
"""
from __future__ import annotations

import argparse
import os
import subprocess
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=["SHADOW", "DRY_RUN", "LIVE"], default="SHADOW")
    parser.add_argument("--ha", action="store_true")
    parser.add_argument("--badge", action="store_true")
    parser.add_argument("--auto-flat", action="store_true")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--i-know-what-im-doing", dest="iknow", action="store_true")
    args = parser.parse_args()

    # Load .env if present (simple parser: KEY=VALUE lines)
    env = os.environ.copy()
    env_path = Path(".env")
    if env_path.exists():
        for line in env_path.read_text().splitlines():
            if not line or line.strip().startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            env.setdefault(k.strip(), v.strip())

    # Overlay flags
    env["EXECUTOR_MODE"] = args.mode
    env.setdefault("ENV", "dev")
    env["FEATURES_HA_DRILLS"] = "1" if args.ha else env.get("FEATURES_HA_DRILLS", "0")
    env["FEATURES_HA_STATUS_BADGE"] = "1" if args.badge else env.get("FEATURES_HA_STATUS_BADGE", "1")
    env["FEATURES_AUTO_FLAT_ALL_ON_LOCK_LOSS"] = "1" if args.auto_flat else env.get("FEATURES_AUTO_FLAT_ALL_ON_LOCK_LOSS", "0")
    env["FEATURES_AUTO_REGISTER_MT5"] = "1" if args.ha else env.get("FEATURES_AUTO_REGISTER_MT5", "0")

    if args.mode == "LIVE" and not args.iknow:
        env["SAFETY_NO_LIVE"] = "1"
    else:
        env.setdefault("SAFETY_NO_LIVE", "1" if args.mode != "LIVE" else "0")

    # Start uvicorn
    cmd = [
        "uvicorn",
        "ops.dashboard.app:app",
        "--host",
        "0.0.0.0",
        "--port",
        str(args.port),
    ]
    print("Launching:", " ".join(cmd))
    return subprocess.call(cmd, env=env)


if __name__ == "__main__":
    raise SystemExit(main())
