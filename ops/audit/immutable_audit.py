import os, json, hashlib, base64
from datetime import datetime, timezone
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from typing import Optional

AUDIT_DIR = os.path.join(os.path.dirname(__file__), "logs")
os.makedirs(AUDIT_DIR, exist_ok=True)

def _utc_day_key(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%d")

def _rotate_path(ts_utc: datetime) -> str:
    return os.path.join(AUDIT_DIR, f"audit-{_utc_day_key(ts_utc)}.jsonl.enc")

def _load_last_hash(path: str) -> Optional[str]:
    if not os.path.exists(path):
        return None
    # We cannot stream-decrypt easily; trust last line hash by reading ciphertext tail marker file if exists.
    # Simpler: keep a small sidecar file storing last hash.
    hpath = path + ".tail"
    if os.path.exists(hpath):
        return open(hpath, "r").read().strip() or None
    return None

def _store_last_hash(path: str, h: str):
    open(path + ".tail", "w").write(h)

def _derive_key() -> bytes:
    # For demo: derive from env or default fixed dev key — replace with KMS/HSM in production
    secret = os.environ.get("AUDIT_AES_KEY", "dev-test-key-should-be-rotated-32bytes!!!").encode()
    # pad/truncate to 32 bytes
    return (secret + b"0"*32)[:32]

def _encrypt_line(plaintext: bytes) -> bytes:
    key = _derive_key()
    aesgcm = AESGCM(key)
    nonce = os.urandom(12)
    ct = aesgcm.encrypt(nonce, plaintext, None)
    return base64.b64encode(nonce + ct) + b"\n"

def _decrypt_line(b64: bytes) -> bytes:
    key = _derive_key()
    raw = base64.b64decode(b64)
    nonce, ct = raw[:12], raw[12:]
    aesgcm = AESGCM(key)
    return aesgcm.decrypt(nonce, ct, None)

def append_event(evt: dict):
    ts_utc = datetime.now(timezone.utc)
    path = _rotate_path(ts_utc)
    last = _load_last_hash(path) or ""
    payload = {
        "ts_utc": ts_utc.isoformat(),
        "evt": evt.get("evt", "UNKNOWN"),
        "payload": evt.get("payload", {}),
        "hash_prev": last or None,
    }
    # Compute current hash
    h = hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()
    payload["hash_curr"] = h
    line = json.dumps(payload, sort_keys=True).encode()
    # encrypt & append
    with open(path, "ab") as f:
        f.write(_encrypt_line(line))
    _store_last_hash(path, h)

def validate_day(day_iso: str) -> bool:
    path = os.path.join(AUDIT_DIR, f"audit-{day_iso}.jsonl.enc")
    hpath = path + ".tail"
    if not os.path.exists(path):
        return False
    prev = None
    ok = True
    with open(path, "rb") as f:
        for enc in f:
            try:
                dec = _decrypt_line(enc)
            except Exception:
                ok = False
                break
            rec = json.loads(dec.decode())
            if rec.get("hash_prev") != (prev if prev else None):
                ok = False
                break
            prev = rec.get("hash_curr")
    # optional: compare with sidecar tail
    if ok and os.path.exists(hpath):
        ok = open(hpath).read().strip() == (prev or "")
    return ok
