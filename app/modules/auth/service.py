import asyncio
from datetime import UTC, datetime

from argon2.exceptions import InvalidHashError, VerificationError
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.core.exceptions import AppError
from app.core.security import decode, digest, hasher, token

from .models import RefreshToken, User


async def register(db, data):
    try:
        async with db.begin_nested():
            user = User(
                email=str(data.email).lower(),
                password_hash=await asyncio.to_thread(hasher.hash, data.password),
                display_name=data.display_name,
            )
            db.add(user)
            await db.flush()
        return user
    except IntegrityError:
        raise AppError(409, "EMAIL_EXISTS", "Email đã được đăng ký") from None


async def issue(db, user):
    access, _ = token(user.id, "access")
    refresh, expiry = token(user.id, "refresh")
    db.add(RefreshToken(digest=digest(refresh), user_id=user.id, expires_at=expiry))
    await db.flush()
    return {"access_token": access, "refresh_token": refresh}


async def login(db, data):
    user = await db.scalar(select(User).where(User.email == str(data.email).lower()))
    try:
        password_hash = (
            user.password_hash if user else await asyncio.to_thread(hasher.hash, "dummy")
        )
        await asyncio.to_thread(hasher.verify, password_hash, data.password)
    except (VerificationError, InvalidHashError):
        raise AppError(401, "INVALID_CREDENTIALS", "Email hoặc mật khẩu sai") from None
    if user is None:
        raise AppError(401, "INVALID_CREDENTIALS", "Email hoặc mật khẩu sai")
    return await issue(db, user)


async def current_user(db, value):
    data = decode(value, "access")
    user = await db.get(User, int(data["sub"]))
    if user is None:
        raise AppError(401, "INVALID_TOKEN", "Người dùng không tồn tại")
    return user


def require_admin(user):
    if user.role != "admin":
        raise AppError(403, "ADMIN_REQUIRED", "Chỉ quản trị viên được phép")
    return user


async def refresh(db, value):
    data = decode(value, "refresh")
    row = await db.scalar(
        select(RefreshToken).where(RefreshToken.digest == digest(value)).with_for_update()
    )
    if (
        not row
        or row.revoked
        or row.user_id != int(data["sub"])
        or row.expires_at <= datetime.now(UTC)
    ):
        raise AppError(401, "INVALID_TOKEN", "Refresh token đã bị thu hồi")
    row.revoked = True
    return await issue(db, await db.get(User, row.user_id))


async def logout(db, user, value):
    decode(value, "refresh")
    row = await db.scalar(
        select(RefreshToken).where(RefreshToken.digest == digest(value)).with_for_update()
    )
    if row and row.user_id != user.id:
        raise AppError(403, "FORBIDDEN", "Không sở hữu token")
    if row:
        row.revoked = True
    return {"ok": True}


async def update_profile(db, user, data):
    user.display_name = data.display_name
    await db.flush()
    return user
