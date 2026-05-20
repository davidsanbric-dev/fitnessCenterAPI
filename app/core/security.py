from __future__ import annotations

from datetime import datetime, timedelta, timezone
import re

import jwt
from passlib.context import CryptContext

from app.core.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
PASSWORD_PATTERN = re.compile(r"^(?=.*[A-Za-z])(?=.*\d).{8,}$")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def validate_password_strength(password: str) -> None:
    if not PASSWORD_PATTERN.match(password):
        raise ValueError("Password must be at least 8 characters long and include letters and numbers")


def create_token(subject: int, token_type: str, expires_delta: timedelta) -> tuple[str, datetime]:
    expires_at = datetime.now(timezone.utc) + expires_delta
    payload = {
        "sub": str(subject),
        "type": token_type,
        "exp": expires_at,
        "iat": datetime.now(timezone.utc),
    }
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm), expires_at


def create_access_token(user_id: int) -> tuple[str, datetime]:
    return create_token(user_id, "access", timedelta(minutes=settings.access_token_expire_minutes))


def create_refresh_token(user_id: int) -> tuple[str, datetime]:
    return create_token(user_id, "refresh", timedelta(days=settings.refresh_token_expire_days))


def decode_token(token: str) -> dict:
    return jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
