# path: tests/mode/test_shadow_semantics.py
from __future__ import annotations

from pathlib import Path

from adapters.base import BrokerAdapter, Order
from config.settings import settings
from gateway.http.middleware import install_mode_watermark
from fastapi import FastAPI
from fastapi.testclient import TestClient


class DummyLive(BrokerAdapter):
    async def _place_live(self, order: Order):  # pragma: no cover - not hit in SHADOW
        raise AssertionError("LIVE path should not be hit in SHADOW")
    async def _modify_live(self, order_id: str, **kwargs):  # pragma: no cover
        raise AssertionError
    async def _close_all_live(self):  # pragma: no cover
        raise AssertionError


def test_shadow_no_io(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "EXECUTOR_MODE", type("E", (), {"value": "SHADOW"})(), raising=False)
    a = DummyLive()
    _ = Path("logs/shadow").mkdir(parents=True, exist_ok=True)
    ares = __import__("asyncio").get_event_loop().run_until_complete(a.place_order(Order("EURUSD", "BUY", 1)))
    assert ares.status == "SHADOW"
    # ensure a file exists
    p = Path("logs/shadow").glob("shadow-*.jsonl")
    assert any(p)


def test_alias_honeypot_header(monkeypatch):
    app = FastAPI()
    install_mode_watermark(app)
    client = TestClient(app)
    monkeypatch.setattr(settings, "EXECUTOR_MODE", type("E", (), {"value": "SHADOW"})(), raising=False)
    @app.get("/")
    def _r():
        return {"ok": True}
    res = client.get("/")
    assert res.headers.get("X-Wolfe-Mode") == "SHADOW"
