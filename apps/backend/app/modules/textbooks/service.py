import asyncio
import json

from sqlalchemy import column, func, literal, or_, select, union_all
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.exc import IntegrityError

from app.core.exceptions import AppError
from app.modules.auth.service import require_admin
from app.modules.dictionary import service as dictionary
from app.nlp.furigana import content_furigana, japanese_strings, search_text, strip_markup
from app.nlp.normalize import is_vietnamese, kana_normalize
from app.nlp.tokenizer import FORMAL_NOUNS, entry_lemmas, example_lemmas, lemmas

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


async def textbook_readings(db, textbook_id, additional_ids=()):
    return await dictionary.headword_readings(
        db,
        select(Entry.word_id)
        .join(Lesson, Lesson.id == Entry.lesson_id)
        .where(Lesson.textbook_id == textbook_id),
        additional_ids,
        select(Entry.word_id)
        .join(Lesson, Lesson.id == Entry.lesson_id)
        .join(Textbook, Textbook.id == Lesson.textbook_id)
        .where(Textbook.visibility == "public"),
    )


def entry_content(entry, furigana=True):
    return (
        entry.content_furigana if furigana and entry.content_furigana is not None else entry.content
    )


def entry_output(entry, furigana=True):
    return {
        "id": entry.id,
        "word_id": entry.word_id,
        "lesson_id": entry.lesson_id,
        "order_no": entry.order_no,
        "content": entry_content(entry, furigana),
        "search_text": entry.search_text,
        "version": entry.version,
        "auto_furigana": entry.auto_furigana,
    }


async def save_entry(
    db, user, lesson_id, word_id, order_no, content, auto_furigana=True, *, readings=None
):
    lesson = await get_lesson(db, user, lesson_id, True)
    word = await dictionary.get_word(db, word_id)
    blocks = validate_content(content)
    if len(json.dumps(blocks, ensure_ascii=False).encode()) > 16000:
        raise AppError(422, "ENTRY_TOO_LARGE", "Nội dung một mục từ vượt 16 KB")
    entry = await db.scalar(
        select(Entry).where(Entry.lesson_id == lesson_id, Entry.word_id == word_id)
    )
    if not entry:
        entry = Entry(lesson_id=lesson_id, word_id=word_id)
        db.add(entry)
    else:
        entry.version += 1
    entry.order_no, entry.content, entry.search_text = order_no, blocks, search_text(blocks)
    entry.lemmas, entry.example_lemmas = await asyncio.to_thread(
        lambda: (entry_lemmas(blocks), example_lemmas(blocks))
    )
    if readings is None:
        readings = (
            await textbook_readings(db, lesson.textbook_id)
            if auto_furigana and any(japanese_strings(blocks))
            else {}
        )
    readings = dict(readings)
    if word.kanji:
        readings[word.kanji] = word.kana
    entry.auto_furigana = auto_furigana
    entry.content_furigana = (
        await asyncio.to_thread(content_furigana, blocks, readings) if auto_furigana else None
    )
    await db.flush()
    return entry


async def create_entry(db, user, lesson_id, data):
    await get_lesson(db, user, lesson_id, True)
    from app.modules.notebook.service import require_word

    try:
        async with db.begin_nested():
            if data.word_id is not None:
                word = await require_word(db, user, data.word_id)
            else:
                candidates = await dictionary.match(db, data.kanji, data.kana)
                exact = [w for w in candidates if w.kanji == data.kanji and w.kana == data.kana]
                word = (
                    exact[0] if exact else await dictionary.create_word(db, data.kanji, data.kana)
                )
            exists = await db.scalar(
                select(Entry.id).where(Entry.lesson_id == lesson_id, Entry.word_id == word.id)
            )
            if exists:
                raise AppError(409, "ENTRY_EXISTS", "Từ đã có trong bài")
            entry = await save_entry(
                db,
                user,
                lesson_id,
                word.id,
                data.order_no,
                [b.model_dump(exclude_none=True) for b in data.content],
                data.auto_furigana,
            )
        return entry_output(entry)
    except IntegrityError:
        raise AppError(409, "ENTRY_EXISTS", "Từ đã có trong bài hoặc được tạo đồng thời") from None


async def patch_entry(db, user, entry_id, data):
    entry = await get_entry(db, user, entry_id)
    await get_lesson(db, user, entry.lesson_id, True)
    # Refresh under a row lock; the stale version must be checked after locking.
    entry = await db.scalar(
        select(Entry)
        .where(Entry.id == entry_id)
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    if entry is None:
        raise AppError(404, "ENTRY_NOT_FOUND", "Không tìm thấy mục từ")
    if entry.version != data.if_match:
        raise AppError(409, "ENTRY_CONFLICT", "Mục từ đã thay đổi; tải lại trước khi sửa")
    blocks = (
        [b.model_dump(exclude_none=True) for b in data.content]
        if data.content is not None
        else entry.content
    )
    entry = await save_entry(
        db,
        user,
        entry.lesson_id,
        entry.word_id,
        data.order_no if data.order_no is not None else entry.order_no,
        blocks,
        data.auto_furigana if data.auto_furigana is not None else entry.auto_furigana,
    )
    return entry_output(entry)


async def delete_entry(db, user, entry_id):
    entry = await get_entry(db, user, entry_id)
    await get_lesson(db, user, entry.lesson_id, True)
    await db.delete(entry)
    await db.flush()
    return {"ok": True}


async def visible_entries(db, user, word_ids=None, textbook_ids=None, query=None, furigana=True):
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
            "content": entry_content(e, furigana),
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


def example_key(word):
    return word["kanji"] or kana_normalize(word["kana"])


async def notebook_entries(db, user, word_ids, *, content=False):
    columns = [
        Entry.word_id,
        Textbook.id.label("textbook_id"),
        Textbook.name.label("textbook"),
        Lesson.id.label("lesson_id"),
        Lesson.title.label("lesson"),
        Entry.order_no,
    ]
    if content:
        columns += [
            func.coalesce(Entry.content_furigana, Entry.content).label("content"),
            Textbook.owner_id,
        ]
    rows = (
        (
            await db.execute(
                select(*columns)
                .join(Lesson, Lesson.id == Entry.lesson_id)
                .join(Textbook, Textbook.id == Lesson.textbook_id)
                .where(visible(user), Entry.word_id.in_(word_ids))
                .order_by(Textbook.id, Lesson.number, Entry.order_no, Entry.id)
            )
        )
        .mappings()
        .all()
    )
    return [dict(row) for row in rows]


def example_entries(user, word):
    # Keep the GIN containment operator on the unmodified array column.
    return (
        select(Entry.id)
        .join(Lesson, Lesson.id == Entry.lesson_id)
        .join(Textbook, Textbook.id == Lesson.textbook_id)
        .where(
            visible(user),
            Entry.word_id != word["id"],
            Entry.example_lemmas.contains([example_key(word)]),
        )
    )


async def example_counts(db, user, words):
    statements = []
    for word in words:
        if example_key(word) and example_key(word) not in FORMAL_NOUNS:
            sample = example_entries(user, word).limit(1001).subquery()
            statements.append(
                select(
                    literal(word["id"]).label("word_id"), func.count(sample.c.id).label("observed")
                ).select_from(sample)
            )
    if not statements:
        return {}
    rows = (await db.execute(union_all(*statements))).all()
    return {
        row.word_id: {"count": min(row.observed, 1000), "capped": row.observed > 1000}
        for row in rows
    }


def example_sentences(content, key):
    for block in content:
        if block["type"] == "example":
            candidates = [block["ja"]]
        elif block["type"] == "usage":
            candidates = [block.get("context"), *(v["ja"] for v in block.get("variants", []))]
        else:
            continue
        for sentence in candidates:
            if sentence and key in lemmas(strip_markup(sentence).replace("__", "")):
                yield {"ja": sentence, "vi": block.get("vi")}


def ocr_review_required(content):
    return any(
        block["type"] == "raw"
        and isinstance(block.get("data"), dict)
        and any(
            block["data"].get(key) is True
            for key in ("ocr_review_required", "ocr_review", "review_required")
        )
        for block in content
    )


async def word_examples(db, user, word, page, size):
    key = example_key(word)
    if not key:
        return {"items": [], "total": 0, "page": page, "size": size}
    sample = example_entries(user, word).limit(1001).subquery()
    observed = await db.scalar(select(func.count(sample.c.id)))
    rows = (
        await db.execute(
            select(Entry, Lesson, Textbook)
            .join(Lesson, Lesson.id == Entry.lesson_id)
            .join(Textbook, Textbook.id == Lesson.textbook_id)
            .where(Entry.id.in_(example_entries(user, word)))
            .order_by(Textbook.id, Lesson.number, Entry.order_no, Entry.id)
            .offset((page - 1) * size)
            .limit(size)
        )
    ).all()

    def extract():
        return [
            {
                "sentences": list(example_sentences(entry_content(entry), key)),
                "textbook": book.name,
                "textbook_id": book.id,
                "lesson": lesson.title,
                "lesson_id": lesson.id,
                "order_no": entry.order_no,
                "entry_id": entry.id,
                "source_word_id": entry.word_id,
                "ocr_review_required": ocr_review_required(entry.content),
            }
            for entry, lesson, book in rows
        ]

    items = await asyncio.to_thread(extract)
    words = await dictionary.all_by_ids(db, {item["source_word_id"] for item in items})
    descriptions = {
        w.id: d for w, d in zip(words, await dictionary.describe_many(db, words), strict=True)
    }
    for item in items:
        item["source_word"] = descriptions[item.pop("source_word_id")]
    return {
        "items": items,
        "total": min(observed, 1000),
        "total_capped": observed > 1000,
        "page": page,
        "size": size,
    }
