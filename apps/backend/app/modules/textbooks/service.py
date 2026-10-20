import asyncio
import json

from sqlalchemy import column, func, or_, select
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.exc import IntegrityError

from app.core.exceptions import AppError
from app.modules.auth.service import require_admin
from app.modules.dictionary import service as dictionary
from app.nlp.furigana import search_text
from app.nlp.normalize import is_vietnamese
from app.nlp.tokenizer import entry_lemmas

from .blocks import validate_content
from .models import Entry, Lesson, Textbook


def visible(user):
    return or_(Textbook.visibility == "public", Textbook.owner_id == user.id)


async def get_textbook(db, user, textbook_id, write=False):
    book = await db.get(Textbook, textbook_id)
    if not book or (book.owner_id != user.id and (write or book.visibility != "public")):
        raise AppError(404, "TEXTBOOK_NOT_FOUND", "Không tìm thấy giáo trình")
    return book


def check_public(user, data):
    if data.get("visibility") == "public":
        require_admin(user)
        if "commercial" in (data.get("license") or "").lower():
            raise AppError(422, "PRIVATE_REQUIRED", "Giáo trình thương mại phải private")


async def create_textbook(db, user, data):
    values = data.model_dump(mode="json")
    check_public(user, values)
    book = Textbook(owner_id=user.id, **values)
    db.add(book)
    await db.flush()
    return book


async def list_textbooks(db, user, page, size):
    stmt = select(Textbook).where(visible(user))
    total = await db.scalar(select(func.count()).select_from(stmt.subquery()))
    rows = (
        await db.scalars(stmt.order_by(Textbook.id).offset((page - 1) * size).limit(size))
    ).all()
    return {"items": rows, "total": total, "page": page, "size": size}


async def patch_textbook(db, user, textbook_id, data):
    book = await get_textbook(db, user, textbook_id, True)
    values = data.model_dump(mode="json", exclude_unset=True)
    merged = {"visibility": book.visibility, "license": book.license, **values}
    if merged["visibility"] is None or values.get("name", book.name) is None:
        raise AppError(422, "INVALID_TEXTBOOK", "Tên và visibility không được null")
    check_public(user, merged)
    if merged["visibility"] == "public":
        from app.modules.imports.service import has_mimikara_import

        if await has_mimikara_import(db, textbook_id):
            raise AppError(422, "PRIVATE_REQUIRED", "Giáo trình đã import Mimikara phải private")
    for key, value in values.items():
        setattr(book, key, value)
    await db.flush()
    return book


async def delete_textbook(db, user, textbook_id):
    book = await get_textbook(db, user, textbook_id, True)
    await db.delete(book)
    await db.flush()
    return {"ok": True}


async def get_lesson(db, user, lesson_id, write=False):
    lesson = await db.get(Lesson, lesson_id)
    if not lesson:
        raise AppError(404, "LESSON_NOT_FOUND", "Không tìm thấy bài học")
    await get_textbook(db, user, lesson.textbook_id, write)
    return lesson


async def create_lesson(db, user, textbook_id, number, title):
    await get_textbook(db, user, textbook_id, True)
    try:
        async with db.begin_nested():
            lesson = Lesson(textbook_id=textbook_id, number=number, title=title)
            db.add(lesson)
            await db.flush()
        return lesson
    except IntegrityError:
        raise AppError(409, "LESSON_EXISTS", "Số bài học đã tồn tại") from None


async def ensure_lesson(db, user, textbook_id, number):
    await get_textbook(db, user, textbook_id, True)
    lesson = await db.scalar(
        select(Lesson).where(Lesson.textbook_id == textbook_id, Lesson.number == number)
    )
    return lesson or await create_lesson(db, user, textbook_id, number, f"Unit {number}")


async def list_lessons(db, user, textbook_id):
    await get_textbook(db, user, textbook_id)
    return (
        await db.scalars(
            select(Lesson).where(Lesson.textbook_id == textbook_id).order_by(Lesson.number)
        )
    ).all()


async def patch_lesson(db, user, lesson_id, data):
    lesson = await get_lesson(db, user, lesson_id, True)
    values = data.model_dump(exclude_unset=True)
    if any(v is None for v in values.values()):
        raise AppError(422, "INVALID_LESSON", "Trường bài học không được null")
    try:
        async with db.begin_nested():
            for key, value in values.items():
                setattr(lesson, key, value)
            await db.flush()
        return lesson
    except IntegrityError:
        raise AppError(409, "LESSON_EXISTS", "Số bài học đã tồn tại") from None


async def delete_lesson(db, user, lesson_id):
    await db.delete(await get_lesson(db, user, lesson_id, True))
    await db.flush()
    return {"ok": True}


async def list_entries(db, user, lesson_id, page, size):
    await get_lesson(db, user, lesson_id)
    stmt = select(Entry).where(Entry.lesson_id == lesson_id)
    total = await db.scalar(select(func.count()).select_from(stmt.subquery()))
    rows = (
        await db.scalars(
            stmt.order_by(Entry.order_no, Entry.id).offset((page - 1) * size).limit(size)
        )
    ).all()
    return {"items": rows, "total": total, "page": page, "size": size}


async def get_entry(db, user, entry_id):
    entry = await db.get(Entry, entry_id)
    if not entry:
        raise AppError(404, "ENTRY_NOT_FOUND", "Không tìm thấy mục từ")
    await get_lesson(db, user, entry.lesson_id)
    return entry


async def save_entry(db, user, lesson_id, word_id, order_no, content):
    await get_lesson(db, user, lesson_id, True)
    await dictionary.get_word(db, word_id)
    blocks = validate_content(content)
    if len(json.dumps(blocks, ensure_ascii=False).encode()) > 16000:
        raise AppError(422, "ENTRY_TOO_LARGE", "Nội dung một mục từ vượt 16 KB")
    entry = await db.scalar(
        select(Entry).where(Entry.lesson_id == lesson_id, Entry.word_id == word_id)
    )
    if not entry:
        entry = Entry(lesson_id=lesson_id, word_id=word_id)
        db.add(entry)
    entry.order_no, entry.content, entry.search_text = order_no, blocks, search_text(blocks)
    entry.lemmas = await asyncio.to_thread(entry_lemmas, blocks)
    await db.flush()
    return entry


async def visible_entries(db, user, word_ids=None, textbook_ids=None, query=None):
    stmt = (
        select(Entry, Lesson, Textbook)
        .join(Lesson, Lesson.id == Entry.lesson_id)
        .join(Textbook, Textbook.id == Lesson.textbook_id)
        .where(visible(user))
    )
    if word_ids is not None:
        stmt = stmt.where(Entry.word_id.in_(word_ids))
    if textbook_ids:
        stmt = stmt.where(Textbook.id.in_(textbook_ids))
    if query:
        escaped = query.replace("\\", "\\\\").replace("%", r"\%").replace("_", r"\_")
        stmt = stmt.where(
            or_(
                Entry.search_text.ilike("%" + escaped + "%", escape="\\"),
                func.similarity(Entry.search_text, query) >= 0.3,
            )
        )
    rows = (
        await db.execute(stmt.order_by(Textbook.id, Lesson.number, Entry.order_no, Entry.id))
    ).all()
    return [
        {
            "word_id": e.word_id,
            "textbook_id": b.id,
            "textbook": b.name,
            "lesson": l.title,
            "order_no": e.order_no,
            "content": e.content,
            "summary": e.search_text[:200],
        }
        for e, l, b in rows
    ]


def visible_word_ids(user, textbook_ids=None, query=None):
    """Composable read query; callers do not need access to textbook models."""
    stmt = (
        select(Entry.word_id)
        .join(Lesson, Lesson.id == Entry.lesson_id)
        .join(Textbook, Textbook.id == Lesson.textbook_id)
        .where(visible(user))
    )
    if textbook_ids:
        stmt = stmt.where(Textbook.id.in_(textbook_ids))
    if query:
        if is_vietnamese(query):
            blocks = func.jsonb_array_elements(Entry.content).table_valued(column("value", JSONB))
            stmt = stmt.where(
                select(1)
                .select_from(blocks)
                .where(
                    blocks.c.value["type"].astext == "meaning",
                    dictionary.text_match_condition(blocks.c.value["vi"].astext, query),
                )
                .exists()
            )
        else:
            stmt = stmt.where(dictionary.text_match_condition(Entry.search_text, query))
    return stmt
