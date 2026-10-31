"""Пароли (Argon2) и токены (JWT)."""

import secrets
from datetime import datetime, timedelta, timezone

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError

from app.config import get_settings

_hasher = PasswordHasher()
# Хэш-пустышка: сверяем с ним, если пользователя нет, чтобы время ответа не выдавало,
# зарегистрирован ли такой email.
_DUMMY_HASH = _hasher.hash(secrets.token_urlsafe(16))

ALGORITHM = "HS256"


def hash_password(password: str) -> str:
    return _hasher.hash(password)


def verify_password(password: str, password_hash: str | None) -> bool:
    try:
        return _hasher.verify(password_hash or _DUMMY_HASH, password) and password_hash is not None
    except (VerificationError, InvalidHashError):
        return False


# Код восстановления: 12 символов без похожих 0/O и 1/I, показывается как K7M2-QX9R-4TPD.
RECOVERY_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
RECOVERY_LENGTH = 12


def generate_recovery_code() -> str:
    raw = "".join(secrets.choice(RECOVERY_ALPHABET) for _ in range(RECOVERY_LENGTH))
    return "-".join(raw[i : i + 4] for i in range(0, RECOVERY_LENGTH, 4))


def normalize_recovery_code(code: str) -> str:
    """Дефисы, пробелы и регистр не важны: K7M2 qx9r-4tpd == K7M2-QX9R-4TPD."""
    return "".join(ch for ch in code.upper() if ch.isalnum())


def create_token(user_id: int, token_type: str, token_version: int) -> str:
    settings = get_settings()
    lifetime = (
        timedelta(minutes=settings.access_token_minutes)
        if token_type == "access"
        else timedelta(days=settings.refresh_token_days)
    )
    # Реальное время, а не timeutil.utcnow(): срок токена не должен зависеть от подмены
    # «текущего дня» в тестах.
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user_id),
        "type": token_type,
        "tv": token_version,
        "iat": now,
        "exp": now + lifetime,
    }
    return jwt.encode(payload, settings.secret_key, algorithm=ALGORITHM)


def decode_token(token: str, expected_type: str) -> dict | None:
    """Возвращает payload или None, если токен неверный, просрочен или другого типа."""
    try:
        payload = jwt.decode(token, get_settings().secret_key, algorithms=[ALGORITHM])
    except jwt.PyJWTError:
        return None
    if payload.get("type") != expected_type:
        return None
    try:
        int(payload["sub"])
    except (KeyError, ValueError):
        return None
    return payload
