# path: gateway/http/middleware.py
from __future__ import annotations

from fastapi import FastAPI

from config.settings import settings


def install_mode_watermark(app: FastAPI) -> None:
    @app.middleware("http")
    async def _mw(request, call_next):  # type: ignore[no-untyped-def]
        resp = await call_next(request)
        resp.headers["X-Wolfe-Mode"] = getattr(settings.EXECUTOR_MODE, "value", str(settings.EXECUTOR_MODE))
        return resp
