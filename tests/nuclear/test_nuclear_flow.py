# path: tests/nuclear/test_nuclear_flow.py
import base64
from datetime import datetime

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from config.settings import settings
from security.nuclear import prague_day_nonce
from server.api.nuclear import re_enable, ResumePayload
from shared.state.nuclear import clear as clear_nuclear, engage as engage_nuclear
from shared.state.nuclear import set_last_nonce
from shared.state.runtime import LockdownState, set_lockdown


@pytest.fixture(autouse=True)
def _reset_state(monkeypatch):
    clear_nuclear()
    set_last_nonce("")
    set_lockdown(LockdownState.SPLIT_BRAIN)
    yield


def _set_pubkey_from_private():
    pk = Ed25519PrivateKey.generate()
    pub = pk.public_key().public_bytes(encoding=__import__("cryptography.hazmat.primitives.serialization", fromlist=["*"]).Encoding.Raw, format=__import__("cryptography.hazmat.primitives.serialization", fromlist=["*"]).PublicFormat.Raw)
    settings.NUCLEAR_PUBKEY = base64.b64encode(pub).decode()
    return pk


def test_reenable_with_valid_signature(monkeypatch):
    engage_nuclear()
    priv = _set_pubkey_from_private()
    nonce = prague_day_nonce()
    sig = base64.b64encode(priv.sign(nonce.encode())).decode()
    out = re_enable(ResumePayload(signature_b64=sig))
    assert out["status"] == "ok"


def test_replay_rejected(monkeypatch):
    engage_nuclear()
    priv = _set_pubkey_from_private()
    nonce = prague_day_nonce()
    sig = base64.b64encode(priv.sign(nonce.encode())).decode()
    out = re_enable(ResumePayload(signature_b64=sig))
    assert out["status"] == "ok"
    with pytest.raises(Exception):
        re_enable(ResumePayload(signature_b64=sig))


def test_invalid_signature_rejected(monkeypatch):
    engage_nuclear()
    _set_pubkey_from_private()
    bad_sig = base64.b64encode(b"not a sig").decode()
    with pytest.raises(Exception):
        re_enable(ResumePayload(signature_b64=bad_sig))


def test_nonce_roll_accepts_new_day(monkeypatch):
    engage_nuclear()
    priv = _set_pubkey_from_private()
    # Simulate yesterday and today by monkeypatching prague_day_nonce
    yesterday = "2000-01-01"
    today = "2000-01-02"
    monkeypatch.setattr("security.nuclear.prague_day_nonce", lambda now=None: yesterday)
    sig1 = base64.b64encode(priv.sign(yesterday.encode())).decode()
    out1 = re_enable(ResumePayload(signature_b64=sig1))
    assert out1["status"] == "ok"

    # re-engage to test second day
    engage_nuclear()
    monkeypatch.setattr("security.nuclear.prague_day_nonce", lambda now=None: today)
    sig2 = base64.b64encode(priv.sign(today.encode())).decode()
    out2 = re_enable(ResumePayload(signature_b64=sig2))
    assert out2["status"] == "ok"
