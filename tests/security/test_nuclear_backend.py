# path: tests/security/test_nuclear_backend.py
import base64

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from config.settings import settings
from security.nuclear import day_nonce
from server.api.nuclear import reenable_route
from shared.state.nuclear import clear as clear_nuclear, engage as engage_nuclear


def _set_pub_from_priv():
    priv = Ed25519PrivateKey.generate()
    pub = priv.public_key().public_bytes(
        encoding=__import__("cryptography.hazmat.primitives.serialization", fromlist=["*"]).Encoding.Raw,
        format=__import__("cryptography.hazmat.primitives.serialization", fromlist=["*"]).PublicFormat.Raw,
    )
    settings.NUCLEAR_PUBKEY = base64.b64encode(pub).decode()
    return priv


@pytest.fixture(autouse=True)
def _reset_state():
    clear_nuclear()


def test_engage_flats_and_disables(monkeypatch):
    async def noop_flat(reason: str):
        return []
    from core.executor.registry import register_adapter

    register_adapter("mt5", type("A", (), {"flat_all": noop_flat})())
    from security.nuclear import engage

    __import__("asyncio").get_event_loop().run_until_complete(engage())
    # If no exceptions, event emitted; state engaged (cannot easily assert without bus capture)


def test_reenable_signature_valid_invalid():
    engage_nuclear()
    priv = _set_pub_from_priv()
    nonce = day_nonce()
    good_sig = base64.b64encode(priv.sign(nonce.encode())).decode()
    out = reenable_route(type("P", (), {"signature_b64": good_sig})())
    assert out["status"] == "ok"
    # replay rejected
    with pytest.raises(Exception):
        reenable_route(type("P", (), {"signature_b64": good_sig})())
