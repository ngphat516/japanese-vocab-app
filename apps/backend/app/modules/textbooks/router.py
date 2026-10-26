from fastapi import APIRouter

from app.common.schemas import DB, Page, Size
from app.modules.auth.dependencies import CurrentUser

from . import schemas as s
from . import service

router = APIRouter(tags=["textbooks"])


@router.get("/textbooks")
async def books(db: DB, user: CurrentUser, page: Page = 1, size: Size = 20):
    return await service.list_textbooks(db, user, page, size)


@router.post("/textbooks", response_model=s.TextbookOut, status_code=201)
async def create(data: s.TextbookCreate, db: DB, user: CurrentUser):
    return await service.create_textbook(db, user, data)


@router.get("/textbooks/{textbook_id}", response_model=s.TextbookOut)
async def get(textbook_id: int, db: DB, user: CurrentUser):
    return await service.get_textbook(db, user, textbook_id)


@router.patch("/textbooks/{textbook_id}", response_model=s.TextbookOut)
async def patch(textbook_id: int, data: s.TextbookPatch, db: DB, user: CurrentUser):
    return await service.patch_textbook(db, user, textbook_id, data)


@router.delete("/textbooks/{textbook_id}")
async def remove(textbook_id: int, db: DB, user: CurrentUser):
    return await service.delete_textbook(db, user, textbook_id)


@router.get("/textbooks/{textbook_id}/lessons", response_model=list[s.LessonOut])
async def lessons(textbook_id: int, db: DB, user: CurrentUser):
    return await service.list_lessons(db, user, textbook_id)


@router.post("/textbooks/{textbook_id}/lessons", response_model=s.LessonOut, status_code=201)
async def create_lesson(textbook_id: int, data: s.LessonCreate, db: DB, user: CurrentUser):
    return await service.create_lesson(db, user, textbook_id, data.number, data.title)


@router.patch("/lessons/{lesson_id}", response_model=s.LessonOut)
async def patch_lesson(lesson_id: int, data: s.LessonPatch, db: DB, user: CurrentUser):
    return await service.patch_lesson(db, user, lesson_id, data)


@router.delete("/lessons/{lesson_id}")
async def delete_lesson(lesson_id: int, db: DB, user: CurrentUser):
    return await service.delete_lesson(db, user, lesson_id)


@router.get("/lessons/{lesson_id}/entries")
async def entries(
    lesson_id: int,
    db: DB,
    user: CurrentUser,
    page: Page = 1,
    size: Size = 20,
    furigana: bool = True,
):
    result = await service.list_entries(db, user, lesson_id, page, size)
    result["items"] = [service.entry_output(e, furigana) for e in result["items"]]
    return result


@router.get("/entries/{entry_id}", response_model=s.EntryOut)
async def entry(entry_id: int, db: DB, user: CurrentUser, furigana: bool = True):
    return service.entry_output(await service.get_entry(db, user, entry_id), furigana)


@router.post("/lessons/{lesson_id}/entries", response_model=s.EntryOut, status_code=201)
async def create_entry(lesson_id: int, data: s.EntryCreate, db: DB, user: CurrentUser):
    return await service.create_entry(db, user, lesson_id, data)


@router.patch("/entries/{entry_id}", response_model=s.EntryOut)
async def patch_entry(entry_id: int, data: s.EntryPatch, db: DB, user: CurrentUser):
    return await service.patch_entry(db, user, entry_id, data)


@router.delete("/entries/{entry_id}")
async def delete_entry(entry_id: int, db: DB, user: CurrentUser):
    return await service.delete_entry(db, user, entry_id)
