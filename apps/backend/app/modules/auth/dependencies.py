from typing import Annotated

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.common.schemas import DB
from app.core.exceptions import AppError

from . import service

bearer = HTTPBearer(auto_error=False)


async def get_user(
    db: DB, credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)]
):
    if not credentials:
        raise AppError(401, "AUTH_REQUIRED", "Cần đăng nhập")
    return await service.current_user(db, credentials.credentials)


CurrentUser = Annotated[object, Depends(get_user)]


async def get_optional_user(
    db: DB, credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)]
):
    """Guest (None) when no token is sent; a bad or expired token is still a 401."""
    if not credentials:
        return None
    return await service.current_user(db, credentials.credentials)


OptionalUser = Annotated[object | None, Depends(get_optional_user)]


async def get_admin(user: CurrentUser):
    return service.require_admin(user)


Admin = Annotated[object, Depends(get_admin)]
