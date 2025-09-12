## MT5 Bridge Setup (Linux bot ↔ Windows MT5)

This guide connects your Linux EX-44 bot to MetaTrader 5 via a lightweight ZeroMQ bridge. The bot stays on Linux; a small Windows process next to your MT5 terminal streams ticks and executes orders.

### Overview
- Linux (EX-44): ZeroMQ client integrated into `MT5Adapter` (LIVE mode)
- Windows: `scripts/mt5_bridge_server.py` publishes ticks and handles order requests using the official MetaTrader5 module

### 1) Windows host prerequisites
- Windows machine (or VPS) with MT5 Terminal running and logged into your broker account
- Python 3.10+ on Windows: https://www.python.org/downloads/windows/
- Install modules in Windows PowerShell:
```
pip install MetaTrader5==5.0.45 pyzmq==25.1.0
```

### 2) Configure environment on Windows
Set environment variables (PowerShell example):
```
$env:BRIDGE_PUB_HOST = "0.0.0.0"          # or 127.0.0.1 if local only
$env:BRIDGE_REQ_HOST = "0.0.0.0"
$env:BRIDGE_PUB_PORT = "5556"
$env:BRIDGE_REQ_PORT = "5557"
$env:BRIDGE_TOKEN    = "<strong-shared-secret>"

$env:MT5_SERVER   = "<YourBrokerServerName>"   # e.g. OANDA-Demo-1
$env:MT5_LOGIN    = "<your-login>"
$env:MT5_PASSWORD = "<your-password>"
$env:WATCHLIST    = "EURUSD,USDCHF,NZDUSD"     # comma-separated
```

Then run the bridge server:
```
python scripts/mt5_bridge_server.py
```
You should see logs indicating PUB/REP sockets bound and MT5 initialized.

Firewall: allow inbound TCP for the chosen ports (default 5556, 5557) or bind to 127.0.0.1 and tunnel via VPN/SSH.

### 3) Linux (EX-44) configuration
Update `config/default.yaml` with the bridge settings (already added):
```
adapters:
  mt5:
    enabled: true
    bridge:
      host: <windows-host-or-vps-ip>
      pub_port: 5556
      req_port: 5557
      token: <strong-shared-secret>
```
Ensure your watchlist symbols match your broker's symbols.

Install dependencies on EX-44:
```
pip install -r requirements.txt
```

### 4) Connectivity test
On EX-44, with the Windows bridge running:
```
export BRIDGE_HOST=<windows-host-or-ip>
export BRIDGE_PUB_PORT=5556
export BRIDGE_REQ_PORT=5557
export BRIDGE_TOKEN=<strong-shared-secret>
export WATCHLIST="EURUSD"

python scripts/test_bridge_connectivity.py
```
Expected:
- Health response with account balance
- A few ticks printed
- An order response `{"ok": true, "order_id": ...}`

### 5) Run the bot in LIVE
Set mode to LIVE and start as usual. The adapter will use the bridge in LIVE mode:
```
export EXECUTOR_MODE=LIVE
export SAFETY_NO_LIVE=0
python scripts/start_live.py
```
Confirm via the API/dashboard that `last_tick` updates and orders return FILLED/REJECTED from the bridge.

### Operational notes
- Security: Use a strong token, restrict ports, and prefer private networking/VPN.
- Resilience: The client auto-reconnects SUB; REQ has short timeouts and retries. If the bridge restarts, the Linux side will recover.
- Symbol mapping: Ensure exact symbol names (e.g., XAUUSD vs GOLD). Update WATCHLIST on both sides.
- Spread/dev: The bridge sends raw `bid/ask` from MT5 `symbol_info_tick`.

### Troubleshooting
- No ticks: Check Windows firewall, token mismatch, wrong host/ports, MT5 not logged in.
- Order rejected: Inspect MT5 `res.retcode`; common causes are market closed, volume step, or wrong symbol.
- Linux shows connected but no trading: Verify `EXECUTOR_MODE=LIVE` and `SAFETY_NO_LIVE=0` and that the MT5 adapter is enabled in config.

