# path: tests/config/test_precedence.py
from __future__ import annotations

import os
from pathlib import Path

import importlib


def test_env_overrides_yaml(tmp_path, monkeypatch):
    # Write YAML with one value
    d = tmp_path / "config"; d.mkdir()
    (d / "default.yaml").write_text("modes:\n  executor_mode: DRY_RUN\n")
    monkeypatch.setenv("EXECUTOR_MODE", "SHADOW")
    monkeypatch.setattr("config.loader.DEFAULT_PATH", d / "default.yaml", raising=False)
    # Reload Settings
    mod = importlib.import_module("config.settings")
    importlib.reload(mod)
    assert mod.settings.EXECUTOR_MODE.value == "SHADOW"


def test_dotenv_overrides_yaml_but_not_env(tmp_path, monkeypatch):
    d = tmp_path / "config"; d.mkdir()
    (d / "default.yaml").write_text("modes:\n  executor_mode: DRY_RUN\n")
    monkeypatch.setattr("config.loader.DEFAULT_PATH", d / "default.yaml", raising=False)
    # Create .env with SHADOW
    env = tmp_path / ".env"
    env.write_text("EXECUTOR_MODE=SHADOW\n")
    monkeypatch.setenv("PYTHONPATH", str(tmp_path), prepend=True)
    # Ensure no ENV var present
    if os.environ.get("EXECUTOR_MODE"):
        del os.environ["EXECUTOR_MODE"]
    # Reload module with dotenv path by cwd
    os.chdir(tmp_path)
    mod = importlib.import_module("config.settings")
    importlib.reload(mod)
    assert mod.settings.EXECUTOR_MODE.value == "SHADOW"
