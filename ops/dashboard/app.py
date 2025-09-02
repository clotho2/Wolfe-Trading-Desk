# path: ops/dashboard/app.py (ensure routers + middleware are mounted)
from __future__ import annotations

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
from server.api.ha import router as ha_router
from server.api.health import router as health_router
from server.api.nuclear import router as nuclear_router

app = FastAPI(title="WolfeDesk v0.4.3 Dashboard")
install_mode_watermark(app)
app.include_router(ha_router)
app.include_router(health_router)
app.include_router(nuclear_router)


@app.on_event("startup")
async def _startup():
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

