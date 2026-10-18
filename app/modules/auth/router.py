from fastapi import APIRouter

from app.common.schemas import DB

from . import schemas as s
from . import service
from .dependencies import CurrentUser

router = APIRouter(tags=["auth"])


@router.post("/auth/register", response_model=s.Profile, status_code=201)
async def register(data: s.Register, db: DB):
    return await service.register(db, data)


@router.post("/auth/login", response_model=s.Tokens)
async def login(data: s.Login, db: DB):
    return await service.login(db, data)


@router.post("/auth/refresh", response_model=s.Tokens)
async def refresh(data: s.Refresh, db: DB):
    return await service.refresh(db, data.refresh_token)


@router.post("/auth/logout")
async def logout(data: s.Refresh, db: DB, user: CurrentUser):
    return await service.logout(db, user, data.refresh_token)


@router.get("/me", response_model=s.Profile)
async def me(user: CurrentUser):
    return user


@router.patch("/me", response_model=s.Profile)
async def patch_me(data: s.ProfilePatch, db: DB, user: CurrentUser):
    return await service.update_profile(db, user, data)
