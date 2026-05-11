from datetime import UTC, datetime, timedelta
from typing import Any, cast

import bcrypt
from jose import ExpiredSignatureError, JWTError, jwt

from app.config import settings


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))


def create_access_token(data: dict[str, Any]) -> str:
    to_encode = data.copy()
    expire = datetime.now(UTC) + timedelta(
        minutes=settings.jwt_access_token_expire_minutes,
    )
    to_encode.update({"exp": expire, "type": "access"})
    encoded: str = cast(
        str, jwt.encode(to_encode, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)
    )
    return encoded


def create_refresh_token(data: dict[str, Any]) -> str:
    to_encode = data.copy()
    expire = datetime.now(UTC) + timedelta(days=settings.jwt_refresh_token_expire_days)
    to_encode.update({"exp": expire, "type": "refresh"})
    encoded: str = cast(
        str, jwt.encode(to_encode, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)
    )
    return encoded


def decode_access_token(token: str) -> dict[str, Any] | None:
    try:
        payload: dict[str, Any] = jwt.decode(
            token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm]
        )
        if payload.get("type") != "access":
            return None
        return payload
    except ExpiredSignatureError:
        raise  # 만료 여부를 호출부에서 구분할 수 있도록 전파
    except JWTError:
        return None


def decode_refresh_token(token: str) -> dict[str, Any] | None:
    try:
        payload: dict[str, Any] = jwt.decode(
            token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm]
        )
        if payload.get("type") != "refresh":
            return None
        return payload
    except JWTError:
        return None
