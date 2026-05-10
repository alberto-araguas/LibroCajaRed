import base64
from datetime import datetime, timedelta, timezone
import hashlib
import hmac
import json
import secrets


PASSWORD_ALGORITHM = "pbkdf2_sha256"
PASSWORD_ITERATIONS = 260_000


def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt.encode("utf-8"),
        PASSWORD_ITERATIONS,
    ).hex()
    return f"{PASSWORD_ALGORITHM}${PASSWORD_ITERATIONS}${salt}${digest}"


def verify_password(password: str, password_hash: str) -> bool:
    try:
        algorithm, iterations, salt, digest = password_hash.split("$", 3)
    except ValueError:
        return False
    if algorithm != PASSWORD_ALGORITHM:
        return False

    expected = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt.encode("utf-8"),
        int(iterations),
    ).hex()
    return hmac.compare_digest(expected, digest)


def _base64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode("ascii").rstrip("=")


def _unbase64url(value: str) -> bytes:
    padding = "=" * (-len(value) % 4)
    return base64.urlsafe_b64decode(f"{value}{padding}".encode("ascii"))


def create_access_token(user_id: int, secret: str, expires_minutes: int) -> str:
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=expires_minutes)
    payload = {
        "sub": str(user_id),
        "exp": int(expires_at.timestamp()),
        "nonce": secrets.token_urlsafe(12),
    }
    payload_part = _base64url(json.dumps(payload, separators=(",", ":")).encode("utf-8"))
    signature = hmac.new(secret.encode("utf-8"), payload_part.encode("ascii"), hashlib.sha256).digest()
    return f"{payload_part}.{_base64url(signature)}"


def parse_access_token(token: str, secret: str) -> int | None:
    try:
        payload_part, signature_part = token.split(".", 1)
    except ValueError:
        return None

    expected_signature = hmac.new(
        secret.encode("utf-8"),
        payload_part.encode("ascii"),
        hashlib.sha256,
    ).digest()
    try:
        provided_signature = _unbase64url(signature_part)
    except (ValueError, TypeError):
        return None
    if not hmac.compare_digest(expected_signature, provided_signature):
        return None

    try:
        payload = json.loads(_unbase64url(payload_part))
    except (ValueError, TypeError, json.JSONDecodeError):
        return None

    if int(payload.get("exp", 0)) < int(datetime.now(timezone.utc).timestamp()):
        return None

    subject = payload.get("sub")
    if not subject:
        return None
    try:
        return int(subject)
    except ValueError:
        return None
