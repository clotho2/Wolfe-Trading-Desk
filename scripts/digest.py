from ops.audit.immutable_audit import append_event
from datetime import datetime, timezone

def main():
    append_event({
        "evt": "DAILY_DIGEST",
        "payload": {
            "ts": datetime.now(timezone.utc).isoformat(),
            "pnl": {"daily": 0.0, "weekly": 0.0},
            "reason_codes": [],
            "slippage_slo": {"breaches_24h": 0},
            "adapter_health": {"mt5": "ok"},
        }
    })
    print("Digest written.")

if __name__ == "__main__":
    main()
