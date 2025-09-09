# path: config/loader.py
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

import yaml


DEFAULT_PATH = Path("config/default.yaml")
PROFILE_PATH = Path("config/profile.ftmo.yaml")


def _read_yaml(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    try:
        return yaml.safe_load(path.read_text()) or {}
    except Exception:
        return {}


def _map_yaml_to_env_keys(doc: Dict[str, Any]) -> Dict[str, Any]:
    """Return a dict used as the lowest-precedence settings source.

    Includes both:
      • flat mirrors used by legacy env keys, and
      • nested sections (broker/adapters/watchlist/executor/safety/features)
        so Pydantic can bind them directly to nested models.
    """
    out: Dict[str, Any] = {}

    # ── nested sections (pass-through) ───────────────────────────────────────
    for k in ("broker", "adapters", "watchlist", "executor", "safety", "features"):
        if k in doc:
            out[k] = doc[k]

    # ── existing mirrors (keep legacy env support) ───────────────────────────
    mode = (doc.get("modes", {}) or {}).get("executor_mode")
    if mode:
        out["EXECUTOR_MODE"] = str(mode).upper()

    corr = doc.get("correlation", {}) or {}
    if "window_days" in corr:
        out["CORR_WINDOW_DAYS"] = int(corr["window_days"])
    if "block_threshold" in corr:
        out["CORR_BLOCK_THRESHOLD"] = float(corr["block_threshold"])
    if "block_threshold_action" in corr:
        out["CORR_THRESHOLD_ACTION"] = str(corr["block_threshold_action"]).lower()
    if "dxy_band_pct" in corr:
        out["DXY_BAND_PCT"] = float(corr["dxy_band_pct"])

    gap = doc.get("gap", {}) or {}
    if "alert_pct" in gap:
        out["GAP_ALERT_PCT"] = float(gap["alert_pct"])

    feats = doc.get("features", {}) or {}
    if "ha_drills" in feats:
        out["FEATURES_HA_DRILLS"] = bool(feats["ha_drills"])  # noqa: FBT003
    if "ha_status_badge" in feats:
        out["FEATURES_HA_STATUS_BADGE"] = bool(feats["ha_status_badge"])  # noqa: FBT003
    if "auto_flat_all_on_lock_loss" in feats:
        out["FEATURES_AUTO_FLAT_ALL_ON_LOCK_LOSS"] = bool(feats["auto_flat_all_on_lock_loss"])  # noqa: FBT003
    if "auto_register_mt5" in feats:
        out["FEATURES_AUTO_REGISTER_MT5"] = bool(feats["auto_register_mt5"])  # noqa: FBT003
    if "gap_guard" in feats:
        out["FEATURES_GAP_GUARD"] = bool(feats["gap_guard"])  # noqa: FBT003
    if "risk_adapter" in feats:
        out["FEATURES_RISK_ADAPTER"] = bool(feats["risk_adapter"])  # noqa: FBT003

    risk = doc.get("risk", {}) or {}
    if "mode" in risk:
        out["RISK_MODE"] = str(risk["mode"]).lower()
    if "floor_pct" in risk:
        out["RISK_FLOOR_PCT"] = float(risk["floor_pct"])
    if "ceiling_pct" in risk:
        out["RISK_CEILING_PCT"] = float(risk["ceiling_pct"])

    ftmo = doc.get("ftmo", {}) or {}
    if "phase1_pacing_bonus_pct" in ftmo:
        out["FTMO_PHASE1_PACING_BONUS_PCT"] = float(ftmo["phase1_pacing_bonus_pct"])
    if "phase2_max_per_trade_risk_pct" in ftmo:
        out["FTMO_PHASE2_MAX_PER_TRADE_RISK_PCT"] = float(ftmo["phase2_max_per_trade_risk_pct"])
    if "friday_cutoff_gmt" in ftmo:
        out["FTMO_FRIDAY_CUTOFF_GMT"] = str(ftmo["friday_cutoff_gmt"])  # "HH:MM"

    prof = (doc.get("profile") or "").strip().lower()
    if prof:
        out["PROFILE"] = prof

    # Leader / Redis optional mirrors
    leader = doc.get("leader", {}) or {}
    if "lock_ttl_ms" in leader:
        out["LOCK_TTL_MS"] = int(leader["lock_ttl_ms"])
    if "heartbeat_ms" in leader:
        out["HEARTBEAT_MS"] = int(leader["heartbeat_ms"])
    if "lock_key" in leader:
        out["HA_LOCK_KEY"] = str(leader["lock_key"]) 
    if "redis_url" in leader:
        out["REDIS_URL"] = str(leader["redis_url"]) 

    return out


def yaml_settings_source() -> Dict[str, Any]:
    base = _map_yaml_to_env_keys(_read_yaml(DEFAULT_PATH))
    prof_doc = _read_yaml(PROFILE_PATH)
    profile = _map_yaml_to_env_keys(prof_doc) if prof_doc else {}
    base.update(profile)
    return base

