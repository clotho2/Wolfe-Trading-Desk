# path: ops/dashboard/app.py (root badge gated by FEATURES_HA_STATUS_BADGE)
from __future__ import annotations

from typing import Optional

from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel

from config.settings import ExecutorMode, Settings, settings
from engine.timebox import now_prague, prague_reset_countdown
from ops.audit.immutable_audit import append_event
from ops.ha.bootstrap import start_ha, status as ha_status

app = FastAPI(title="WolfeDesk v0.4.3 Dashboard")


@app.on_event("startup")
async def _startup():
    await start_ha(app, Settings())


def require_token(authorization: Optional[str] = Header(None)):
    token = (authorization or "").removeprefix("Bearer ").strip()
    if token != settings.DASH_TOKEN:
        raise HTTPException(status_code=401, detail="Unauthorized")
    return True


@app.middleware("http")
async def mode_header(request, call_next):  # type: ignore[no-untyped-def]
    response = await call_next(request)
    response.headers["X-Wolfe-Mode"] = settings.EXECUTOR_MODE.value
    return response


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
<link rel=\"icon\" href=\"data:,\" />
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


@app.get("/health")
def health():
    return {"status": "ok", "mode": settings.EXECUTOR_MODE.value}


@app.get("/snapshot", dependencies=[Depends(require_token)])
def snapshot():
    np = now_prague()
    return {"prague_now": np.isoformat(), "reset_in_seconds": int(prague_reset_countdown(np).total_seconds()), "mode": settings.EXECUTOR_MODE.value}


@app.get("/ha/status", dependencies=[Depends(require_token)])
def ha_status_route():
    return ha_status()


@app.get("/ui/ha", response_class=HTMLResponse)
def ui_ha():
    return """
<!doctype html>
<meta charset=\"utf-8\" />
<title>WolfeDesk HA Status</title>
<style>
  body { font-family: ui-sans-serif, system-ui; padding: 16px; }
  .chip { display: inline-flex; align-items: center; gap: 8px; padding: 6px 10px; border-radius: 999px; background: #eee; color: #333; }
  .chip.leader { background: #d1fae5; color: #065f46; }
  .chip.follower { background: #e5e7eb; color: #374151; }
  .chip.off { background: #f3f4f6; color: #6b7280; }
  .meta { font-size: 12px; color: #6b7280; margin-top: 8px; }
</style>
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


@app.post("/kill", dependencies=[Depends(require_token)])
def kill(payload: KillConfirm):
    if not payload.confirm:
        raise HTTPException(status_code=400, detail="Confirmation required")
    evt = {"evt": "KILL_ALL", "payload": {"mode": settings.EXECUTOR_MODE.value, "simulated": settings.EXECUTOR_MODE != ExecutorMode.LIVE}}
    append_event(evt)
    return JSONResponse({"status": "ok", "message": "Kill issued", "simulated": settings.EXECUTOR_MODE != ExecutorMode.LIVE})

