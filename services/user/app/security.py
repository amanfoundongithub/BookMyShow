from datetime import datetime, timedelta, timezone
from typing import Any
import jwt
from pwdlib import PasswordHash
from .config import settings

_password_hash = PasswordHash.recommended()


def hash_password(plain_password: str) -> str:
    return _password_hash.hash(plain_password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return _password_hash.verify(plain_password, hashed_password)


def create_access_token(*, user_id: str, email: str, role: str = "USER") -> str:
    now = datetime.now(timezone.utc)
    payload: dict[str, Any] = {
        "sub": user_id,
        "user_id": user_id,
        "email": email,
        "role": role,
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(minutes=settings.JWT_EXPIRES_MINUTES)).timestamp()),
    }
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


def decode_access_token(token: str) -> dict[str, Any]:
    return jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])