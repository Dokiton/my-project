import base64
import hashlib
import hmac
import json
import secrets
import time
from uuid import UUID

SECRET_KEY = "educational-ai-platform-super-secret-key-change-in-production"


def get_password_hash(password: str) -> str:
    """Құпиясөзді PBKDF2-HMAC-SHA256 және тұз (salt) арқылы хэштеу."""
    salt = secrets.token_hex(16)
    key = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt.encode("utf-8"),
        100_000,
    )
    return f"{salt}${key.hex()}"


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Енгізілген құпиясөзді сақталған хэшпен салыстыру."""
    try:
        salt, key_hex = hashed_password.split("$", 1)
        expected_key = hashlib.pbkdf2_hmac(
            "sha256",
            plain_password.encode("utf-8"),
            salt.encode("utf-8"),
            100_000,
        )
        return hmac.compare_digest(expected_key.hex(), key_hex)
    except (ValueError, AttributeError):
        return False


def create_access_token(user_id: UUID | str, role: str, expires_in: int = 86400) -> str:
    """HMAC-SHA256 қолтаңбасы бар Bearer Access Token жасау."""
    payload = {
        "sub": str(user_id),
        "role": role,
        "exp": int(time.time()) + expires_in,
    }
    payload_raw = json.dumps(payload, separators=(",", ":")).encode("utf-8")
    payload_b64 = base64.urlsafe_b64encode(payload_raw).decode("utf-8").rstrip("=")
    sig = hmac.new(
        SECRET_KEY.encode("utf-8"),
        payload_b64.encode("utf-8"),
        hashlib.sha256,
    ).digest()
    sig_b64 = base64.urlsafe_b64encode(sig).decode("utf-8").rstrip("=")
    return f"{payload_b64}.{sig_b64}"


def decode_access_token(token: str) -> dict | None:
    """Токен қолтаңбасын және мерзімін тексеру."""
    try:
        parts = token.split(".")
        if len(parts) != 2:
            return None
        payload_b64, sig_b64 = parts
        # padding қалпына келтіру
        pad_sig = sig_b64 + "=" * (-len(sig_b64) % 4)
        actual_sig = base64.urlsafe_b64decode(pad_sig)
        expected_sig = hmac.new(
            SECRET_KEY.encode("utf-8"),
            payload_b64.encode("utf-8"),
            hashlib.sha256,
        ).digest()
        if not hmac.compare_digest(expected_sig, actual_sig):
            return None
        pad_payload = payload_b64 + "=" * (-len(payload_b64) % 4)
        payload = json.loads(base64.urlsafe_b64decode(pad_payload).decode("utf-8"))
        if payload.get("exp", 0) < int(time.time()):
            return None
        return payload
    except Exception:
        return None
