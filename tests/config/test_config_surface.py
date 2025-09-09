# path: tests/config/test_config_surface.py
from __future__ import annotations

from config.settings import settings


def test_broker_and_watchlist_present():
    assert settings.broker.mt5.server, "broker.mt5.server should be set from YAML"
    assert settings.broker.mt5.login, "broker.mt5.login should be set from YAML"
    assert isinstance(settings.watchlist, list) and len(settings.watchlist) > 0


def test_nested_overrides_env(monkeypatch):
    # Simulate env override for nested field
    monkeypatch.setenv("BROKER__MT5__SERVER", "OVERRIDE-SERVER")
    # Re-instantiate a new Settings to pick up env
    from importlib import reload
    import config.settings as cs

    reload(cs)
    assert cs.settings.broker.mt5.server == "OVERRIDE-SERVER"
