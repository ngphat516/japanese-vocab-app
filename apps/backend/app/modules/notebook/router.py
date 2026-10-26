import asyncio
from typing import Annotated, Literal
from urllib.parse import quote

from fastapi import APIRouter, Query, Response

from app.common.schemas import DB, Page, Size
from app.modules.auth.dependencies import CurrentUser

from . import exports, service
from . import schemas as s

router = APIRouter(tags=["notebook"])


@router.get("/history", response_model=s.HistoryPage)
async def history(db: DB, user: CurrentUser, page: Page = 1, size: Size = 20):
    return await service.list_history(db, user, page, size)


@router.delete("/history")
async def clear_history(db: DB, user: CurrentUser):
    return await service.clear_history(db, user)


@router.get("/saved-words/stats", response_model=dict[str, int])
async def stats(db: DB, user: CurrentUser):
    return await service.stats(db, user)


@router.get("/saved-words/export")
async def export_words(
    db: DB,
    user: CurrentUser,
    format: Literal["anki", "csv", "markdown"],
    collection_id: Annotated[int | None, Query(gt=0)] = None,
    jlpt: s.JLPT | None = None,
    tag: Annotated[str | None, Query(max_length=100)] = None,
):
    rows = await exports.export_rows(db, user, collection_id=collection_id, jlpt=jlpt, tag=tag)
    content, media_type, extension = await asyncio.to_thread(exports.render, rows, format, user.id)
    filename = f"Sổ từ.{extension}"
    return Response(
        content,
        media_type=media_type,
        headers={
            "Content-Disposition": f"attachment; filename=notebook.{extension}; filename*=UTF-8''{quote(filename)}"
        },
    )


@router.get("/saved-words", response_model=s.SavedPage)
async def saved_words(
    db: DB,
    user: CurrentUser,
    page: Page = 1,
    size: Size = 20,
    jlpt: s.JLPT | None = None,
    tag: Annotated[str | None, Query(max_length=100)] = None,
    textbook_id: Annotated[int | None, Query(gt=0)] = None,
    collection_id: Annotated[int | None, Query(gt=0)] = None,
):
    return await service.list_saved(
        db,
        user,
        page,
        size,
        jlpt=jlpt,
        tag=tag,
        textbook_id=textbook_id,
        collection_id=collection_id,
    )


@router.post("/saved-words", response_model=s.SavedItem, status_code=201)
async def save_word(data: s.SaveWord, db: DB, user: CurrentUser):
    return await service.save_word(db, user, data)


@router.patch("/saved-words/{saved_id}", response_model=s.SavedItem)
async def patch_saved(saved_id: int, data: s.SavedPatch, db: DB, user: CurrentUser):
    return await service.patch_saved(db, user, saved_id, data)


@router.delete("/saved-words/{saved_id}")
async def delete_saved(saved_id: int, db: DB, user: CurrentUser):
    return await service.delete_saved(db, user, saved_id)


@router.get("/collections", response_model=s.CollectionPage)
async def collections(db: DB, user: CurrentUser, page: Page = 1, size: Size = 20):
    return await service.list_collections(db, user, page, size)


@router.post("/collections", response_model=s.CollectionItem, status_code=201)
async def create_collection(data: s.CollectionInput, db: DB, user: CurrentUser):
    return await service.create_collection(db, user, data)


@router.patch("/collections/{collection_id}", response_model=s.CollectionItem)
async def patch_collection(collection_id: int, data: s.CollectionInput, db: DB, user: CurrentUser):
    return await service.patch_collection(db, user, collection_id, data)


@router.delete("/collections/{collection_id}")
async def delete_collection(collection_id: int, db: DB, user: CurrentUser):
    return await service.delete_collection(db, user, collection_id)


@router.post("/collections/{collection_id}/words", response_model=s.CollectionItem)
async def add_members(collection_id: int, data: s.CollectionMembers, db: DB, user: CurrentUser):
    return await service.collection_members(db, user, collection_id, data.saved_word_ids)


@router.delete("/collections/{collection_id}/words", response_model=s.CollectionItem)
async def remove_members(collection_id: int, data: s.CollectionMembers, db: DB, user: CurrentUser):
    return await service.collection_members(
        db, user, collection_id, data.saved_word_ids, remove=True
    )
