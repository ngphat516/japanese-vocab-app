import hashlib
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import jwt
from argon2 import PasswordHasher

from app.core.config import get_settings
from app.core.exceptions import AppError

hasher = PasswordHasher()


def token(user_id, kind):
    now = datetime.now(UTC)
    expiry = now + (timedelta(minutes=15) if kind == "access" else timedelta(days=7))
    value = jwt.encode(
        {"sub": str(user_id), "type": kind, "iat": now, "exp": expiry, "jti": uuid4().hex},
        get_settings().jwt_secret,
        algorithm="HS256",
    )
    return value, expiry


def decode(value, kind):
    try:
        data = jwt.decode(
            value,
            get_settings().jwt_secret,
            algorithms=["HS256"],
            options={"require": ["sub", "exp", "iat", "jti", "type"]},
        )
        if data["type"] != kind:
            raise ValueError("wrong token type")
        int(data["sub"])
        return data
    except (jwt.PyJWTError, ValueError, TypeError):
        raise AppError(401, "INVALID_TOKEN", "Token không hợp lệ hoặc hết hạn") from None


def digest(value):
    return hashlib.sha256(value.encode()).hexdigest()
