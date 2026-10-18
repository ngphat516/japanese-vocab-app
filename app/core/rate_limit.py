from datetime import UTC, datetime

from fastapi import Request
from sqlalchemy import Integer, String, case
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Mapped, mapped_column

from app.core.config import get_settings
from app.core.exceptions import AppError
from app.core.security import decode
from app.db.base import Base
from app.db.session import Session


class RateBucket(Base):
    __tablename__ = "rate_buckets"
    key: Mapped[str] = mapped_column(String(300), primary_key=True)
    window: Mapped[int] = mapped_column(Integer)
    count: Mapped[int] = mapped_column(Integer)


async def check(request: Request):
    if not get_settings().rate_limit_enabled:
        return
    path = request.url.path.removeprefix("/api/v1")
    limit = (
        60 if path == "/search" else 10 if path.startswith("/auth/") or path == "/imports" else 0
    )
    if not limit:
        return
    identity = request.client.host if request.client else "unknown"
    if path == "/search" or path == "/imports":
        credentials = request.headers.get("authorization", "")
        if credentials.lower().startswith("bearer "):
            identity = "user:" + decode(credentials[7:], "access")["sub"]
    key = f"{'search' if limit == 60 else 'auth' if path.startswith('/auth/') else 'imports'}:{identity}"
    window = int(datetime.now(UTC).timestamp()) // 60
    async with Session.begin() as db:
        stmt = insert(RateBucket).values(key=key, window=window, count=1)
        stmt = stmt.on_conflict_do_update(
            index_elements=["key"],
            set_={
                "window": window,
                "count": case((RateBucket.window == window, RateBucket.count + 1), else_=1),
            },
        ).returning(RateBucket.count)
        count = await db.scalar(stmt)
    if count > limit:
        raise AppError(429, "RATE_LIMITED", "Vượt giới hạn request/phút")
