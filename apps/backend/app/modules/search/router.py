from typing import Annotated, Literal

from fastapi import APIRouter, Query

from app.common.schemas import DB, Page, Size
from app.modules.auth.dependencies import CurrentUser

from . import schemas as s
from . import service

router = APIRouter(tags=["search"])


@router.get("/search", response_model=s.SearchResult, response_model_exclude_none=False)
async def search(
    db: DB,
    user: CurrentUser,
    q: Annotated[str, Query(min_length=1, max_length=200)],
    textbook_ids: Annotated[list[int] | None, Query()] = None,
    jlpt: Literal["N1", "N2", "N3", "N4", "N5"] | None = None,
    page: Page = 1,
    size: Size = 20,
    furigana: bool = True,
):
    return await service.search(db, user, q, textbook_ids, jlpt, page, size, furigana)


@router.get("/words/{word_id}", response_model=s.WordDetail)
async def detail(word_id: int, db: DB, user: CurrentUser, furigana: bool = True):
    return await service.word_detail(db, user, word_id, furigana)


@router.get("/words/{word_id}/examples", response_model=s.ExamplesResult)
async def examples(word_id: int, db: DB, user: CurrentUser, page: Page = 1, size: Size = 20):
    return await service.word_examples(db, user, word_id, page, size)
