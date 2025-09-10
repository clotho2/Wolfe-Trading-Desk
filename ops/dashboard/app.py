# path: ops/dashboard/app.py (ensure routers + middleware are mounted)
from __future__ import annotations

import os
from typing import Optional

from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel

from config.settings import ExecutorMode, Settings, settings
from core.executor.bootstrap import start_executor
from core.executor.loop import load_strategies
from engine.timebox import now_prague, prague_reset_countdown
from gateway.http.middleware import install_mode_watermark
from ops.audit.immutable_audit import append_event
from ops.dashboard.dashboard_html import get_dashboard_html
from ops.ha.bootstrap import start_ha, status as ha_status
from server.api.adapter import router as adapter_router
from server.api.ha import router as ha_router
from server.api.health import router as health_router
from server.api.nuclear import router as nuclear_router
from server.api.strategy import router as strategy_router
from server.api.trades import router as trades_router
from server.api.websocket import router as websocket_router

app = FastAPI(title="WolfeDesk v0.4.3 Dashboard")
install_mode_watermark(app)
app.include_router(adapter_router)
app.include_router(ha_router)
app.include_router(health_router)
app.include_router(nuclear_router)
app.include_router(strategy_router)
app.include_router(trades_router)
app.include_router(websocket_router)


@app.on_event("startup")
async def _startup():
    # Print startup banner with effective configuration
    print("\n" + "=" * 60)
    print("WolfeDesk v0.4.3 - Startup Configuration")
    print("=" * 60)
    print(f"Executor Mode: {settings.EXECUTOR_MODE.value if hasattr(settings.EXECUTOR_MODE, 'value') else settings.EXECUTOR_MODE}")
    print(f"Environment: {settings.ENV}")
    print(f"Safety NO_LIVE: {os.environ.get('SAFETY_NO_LIVE', '0')}")
    
    # Adapter status
    mt5_enabled = False
    if hasattr(settings, 'adapters') and hasattr(settings.adapters, 'mt5'):
        mt5_enabled = settings.adapters.mt5.get('enabled', True)
    print(f"MT5 Adapter Enabled: {mt5_enabled}")
    
    # Watchlist info
    watchlist_count = len(settings.watchlist) if hasattr(settings, 'watchlist') else 0
    print(f"Watchlist Count: {watchlist_count}")
    if watchlist_count > 0 and hasattr(settings, 'watchlist'):
        print(f"Watchlist Symbols: {', '.join(settings.watchlist[:5])}{' ...' if watchlist_count > 5 else ''}")
    
    # Feature flags
    print(f"Auto Register MT5: {settings.FEATURES_AUTO_REGISTER_MT5}")
    print(f"Auto Flat on Lock Loss: {settings.FEATURES_AUTO_FLAT_ALL_ON_LOCK_LOSS}")
    print(f"HA Status Badge: {settings.FEATURES_HA_STATUS_BADGE}")
    print(f"Gap Guard: {settings.FEATURES_GAP_GUARD}")
    print(f"Risk Adapter: {settings.FEATURES_RISK_ADAPTER}")
    print(f"Strategy Pilot: {getattr(settings.features, 'strategy_pilot', False) if hasattr(settings, 'features') else False}")
    
    # HA Configuration
    print(f"HA Lock TTL: {settings.LOCK_TTL_MS}ms")
    print(f"HA Heartbeat: {settings.HEARTBEAT_MS}ms")
    
    # Risk Configuration
    print(f"Risk Mode: {settings.RISK_MODE}")
    print(f"Daily Hard DD: {settings.DAILY_HARD_DD_PCT * 100:.1f}%")
    print(f"Daily Soft Freeze: {settings.DAILY_SOFT_FREEZE_PCT * 100:.1f}%")
    
    print("=" * 60)
    print("Starting services...")
    print("=" * 60 + "\n")
    
    await start_ha(app, Settings())
    # Start executor for all environments when strategy pilot is enabled
    if getattr(settings.features, 'strategy_pilot', False) or settings.FEATURES_STRATEGY_PILOT:
        start_executor(Settings())
    
    # Load strategies if feature is enabled
    load_strategies(Settings())
    from core.executor.loop import get_strategy_status
    strategies = get_strategy_status()
    if strategies:
        print(f"Loaded {len(strategies)} strategies: {[s.get('strategy', 'unknown') for s in strategies]}")


def require_token(authorization: Optional[str] = Header(None)):
    token = (authorization or "").removeprefix("Bearer ").strip()
    if token != settings.DASH_TOKEN:
        raise HTTPException(status_code=401, detail="Unauthorized")
    return True


class KillConfirm(BaseModel):
    confirm: bool


@app.get("/")
def root():
    """Redirect to the trading dashboard."""
    from fastapi.responses import RedirectResponse
    return RedirectResponse(url="/dashboard")


@app.get("/dashboard")
def trading_dashboard():
    """Enhanced trading dashboard with real-time visualization."""
    return HTMLResponse(get_dashboard_html())

