from fastapi import APIRouter

from app.common.schemas import DB, Page, Size
from app.modules.auth.dependencies import CurrentUser

from . import service
from .schemas import WordPatch

router = APIRouter(tags=["dictionary"])


@router.patch("/words/{word_id}")
async def patch_word(word_id: int, data: WordPatch, db: DB, user: CurrentUser):
    return await service.patch_hanviet(db, user, word_id, data.hanviet)


@router.get("/kanji/{char}")
async def kanji(char: str, db: DB, user: CurrentUser, page: Page = 1, size: Size = 20):
    return await service.kanji_detail(db, user, char, page, size)
