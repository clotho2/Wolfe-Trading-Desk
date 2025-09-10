# path: ops/dashboard/app.py (ensure routers + middleware are mounted)
from __future__ import annotations

import os
from typing import Optional

from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel

from config.settings import ExecutorMode, Settings, settings
from core.executor.bootstrap import start_executor
from engine.timebox import now_prague, prague_reset_countdown
from gateway.http.middleware import install_mode_watermark
from ops.audit.immutable_audit import append_event
from ops.ha.bootstrap import start_ha, status as ha_status
from server.api.adapter import router as adapter_router
from server.api.ha import router as ha_router
from server.api.health import router as health_router
from server.api.nuclear import router as nuclear_router

app = FastAPI(title="WolfeDesk v0.4.3 Dashboard")
install_mode_watermark(app)
app.include_router(adapter_router)
app.include_router(ha_router)
app.include_router(health_router)
app.include_router(nuclear_router)


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
    if settings.FEATURES_AUTO_REGISTER_MT5 and settings.ENV in {"dev", "test"}:
        start_executor(Settings())


def require_token(authorization: Optional[str] = Header(None)):
    token = (authorization or "").removeprefix("Bearer ").strip()
    if token != settings.DASH_TOKEN:
        raise HTTPException(status_code=401, detail="Unauthorized")
    return True


class KillConfirm(BaseModel):
    confirm: bool


@app.get("/")
def root():
    if not settings.FEATURES_HA_STATUS_BADGE:
        return {"status": "ok"}
    return HTMLResponse(
        """
<!doctype html>
<meta charset=\"utf-8\" />
<title>WolfeDesk</title>
<style>
  body { font-family: ui-sans-serif, system-ui; padding: 16px; }
  .chip { display:inline-flex; align-items:center; gap:8px; padding:6px 10px; border-radius:999px; background:#eee; color:#333; }
  .chip.leader { background:#d1fae5; color:#065f46; }
  .chip.follower { background:#e5e7eb; color:#374151; }
  .chip.off { background:#f3f4f6; color:#6b7280; }
  .meta { font-size:12px; color:#6b7280; margin-top:8px; }
</style>
<h1>WolfeDesk</h1>
<div id=\"chip\" class=\"chip off\">HA OFF</div>
<div id=\"meta\" class=\"meta\"></div>
<script>
  let delay=2000; const max=10000; const auth='';
  async function poll(){
    try{
      const r=await fetch('/ha/status',{headers:auth?{Authorization:'Bearer '+auth}:{}});
      if(!r.ok) throw new Error(r.status);
      const j=await r.json();
      const chip=document.getElementById('chip'); const meta=document.getElementById('meta');
      if(!j.running){ chip.className='chip off'; chip.textContent='HA OFF'; return; }
      chip.className='chip ' + (j.leader?'leader':'follower');
      chip.textContent=(j.leader?'LEADER':'FOLLOWER') + (j.token_tail?('#'+j.token_tail):'');
      meta.textContent=`TTL=${j.ttl_ms}ms · HB=${j.hb_ms}ms · last hb ${j.last_hb_ms_ago??'?'}ms ago`;
      delay=2000;
    }catch(e){ delay=Math.min(max, delay*1.6); }
    setTimeout(poll, delay);
  }
  poll();
</script>
"""
    )

