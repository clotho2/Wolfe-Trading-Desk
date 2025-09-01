# path: config/loader.py (add features.risk_adapter mirror)
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
    out: Dict[str, Any] = {}
    # modes
    mode = (doc.get("modes", {}) or {}).get("executor_mode")
    if mode:
        out["EXECUTOR_MODE"] = str(mode).upper()
    # correlation
    corr = doc.get("correlation", {}) or {}
    if "window_days" in corr:
        out["CORR_WINDOW_DAYS"] = int(corr["window_days"])
    if "block_threshold" in corr:
        out["CORR_BLOCK_THRESHOLD"] = float(corr["block_threshold"])
    if "block_threshold_action" in corr:
        out["CORR_THRESHOLD_ACTION"] = str(corr["block_threshold_action"]).lower()
    if "dxy_band_pct" in corr:
        out["DXY_BAND_PCT"] = float(corr["dxy_band_pct"])
    # gap
    gap = doc.get("gap", {}) or {}
    if "alert_pct" in gap:
        out["GAP_ALERT_PCT"] = float(gap["alert_pct"])
    # features
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
    # risk
    risk = doc.get("risk", {}) or {}
    if "mode" in risk:
        out["RISK_MODE"] = str(risk["mode"]).lower()
    if "floor_pct" in risk:
        out["RISK_FLOOR_PCT"] = float(risk["floor_pct"])
    if "ceiling_pct" in risk:
        out["RISK_CEILING_PCT"] = float(risk["ceiling_pct"])

    prof = (doc.get("profile") or "").strip().lower()
    if prof:
        out["PROFILE"] = prof
    return out


def yaml_settings_source() -> Dict[str, Any]:
    base = _map_yaml_to_env_keys(_read_yaml(DEFAULT_PATH))
    prof_doc = _read_yaml(PROFILE_PATH)
    profile = _map_yaml_to_env_keys(prof_doc) if prof_doc else {}
    base.update(profile)
    return base
