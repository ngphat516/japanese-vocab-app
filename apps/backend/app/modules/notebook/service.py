"""Notebook ownership, history retention and batched read services."""

from sqlalchemy import delete, func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.exc import IntegrityError

from app.core.exceptions import AppError
from app.modules.dictionary import service as dictionary
from app.modules.textbooks import service as textbooks

from .models import Collection, CollectionWord, SavedWord, SearchHistory
from .schemas import normalize_tag


def readable_ids(user, jlpt=None, textbook_id=None):
    entries = textbooks.visible_word_ids(user, [textbook_id] if textbook_id else None)
    return dictionary.readable_ids(entries, jlpt, require_entry=bool(textbook_id))


async def require_word(db, user, word_id):
    if not await db.scalar(
        select(readable_ids(user).where(dictionary.word_id_equals(word_id)).exists())
    ):
        raise AppError(404, "WORD_NOT_FOUND", "Không tìm thấy từ")
    return await dictionary.get_word(db, word_id)


async def fill_saved(db, user, descriptions):
    if not descriptions:
        return
    saved = set(
        (
            await db.scalars(
                select(SavedWord.word_id).where(
                    SavedWord.user_id == user.id,
                    SavedWord.word_id.in_([d["id"] for d in descriptions]),
                )
            )
        ).all()
    )
    for description in descriptions:
        description["saved"] = description["id"] in saved


async def history_lock(db, user):
    # Serialize pruning/upserts for one user, across API processes, until commit.
    await db.execute(select(func.pg_advisory_xact_lock(1312968776, user.id)))


async def record_history(db, user, word, query=None):
    await history_lock(db, user)
    stmt = insert(SearchHistory).values(
        user_id=user.id,
        word_id=word.id,
        query=query or word.kanji or word.kana,
        searched_at=func.clock_timestamp(),
    )
    await db.execute(
        stmt.on_conflict_do_update(
            constraint="uq_history_user_word",
            set_={"searched_at": stmt.excluded.searched_at, "query": stmt.excluded.query},
        )
    )
    old = (
        select(SearchHistory.id)
        .where(SearchHistory.user_id == user.id)
        .order_by(SearchHistory.searched_at.desc(), SearchHistory.id.desc())
        .offset(500)
    )
    await db.execute(delete(SearchHistory).where(SearchHistory.id.in_(old)))


async def source_map(db, user, word_ids):
    sources = {}
    for row in await textbooks.notebook_entries(db, user, word_ids):
        sources.setdefault(row.pop("word_id"), []).append(row)
    return sources


async def list_history(db, user, page, size):
    stmt = select(SearchHistory).where(
        SearchHistory.user_id == user.id, SearchHistory.word_id.in_(readable_ids(user))
    )
    total = await db.scalar(select(func.count()).select_from(stmt.subquery()))
    rows = list(
        (
            await db.scalars(
                stmt.order_by(SearchHistory.searched_at.desc(), SearchHistory.id.desc())
                .offset((page - 1) * size)
                .limit(size)
            )
        ).all()
    )
    words = await dictionary.all_by_ids(db, [r.word_id for r in rows])
    desc = await dictionary.describe_many(db, words)
    await fill_saved(db, user, desc)
    by_word = {w.id: d for w, d in zip(words, desc, strict=True)}
    sources = await source_map(db, user, list(by_word))
    return {
        "items": [
            {
                "id": r.id,
                "word": by_word[r.word_id],
                "query": r.query,
                "searched_at": r.searched_at,
                "sources": sources.get(r.word_id, []),
            }
            for r in rows
        ],
        "total": total,
        "page": page,
        "size": size,
    }


async def clear_history(db, user):
    await history_lock(db, user)
    await db.execute(delete(SearchHistory).where(SearchHistory.user_id == user.id))
    return {"ok": True}


async def get_collection(db, user, collection_id):
    row = await db.scalar(
        select(Collection).where(Collection.id == collection_id, Collection.user_id == user.id)
    )
    if row is None:
        raise AppError(404, "COLLECTION_NOT_FOUND", "Không tìm thấy bộ sưu tập")
    return row


def saved_query(user, jlpt=None, tag=None, textbook_id=None, collection_id=None):
    stmt = select(SavedWord).where(
        SavedWord.user_id == user.id, SavedWord.word_id.in_(readable_ids(user, jlpt, textbook_id))
    )
    if tag is not None:
        stmt = stmt.where(SavedWord.tags.contains([normalize_tag(tag)]))
    if collection_id is not None:
        stmt = stmt.where(
            SavedWord.id.in_(
                select(CollectionWord.saved_word_id).where(
                    CollectionWord.collection_id == collection_id
                )
            )
        )
    return stmt


async def saved_rows(
    db, user, *, jlpt=None, tag=None, textbook_id=None, collection_id=None, page=None, size=None
):
    if collection_id is not None:
        await get_collection(db, user, collection_id)
    stmt = saved_query(user, jlpt, tag, textbook_id, collection_id)
    total = await db.scalar(select(func.count()).select_from(stmt.subquery()))
    stmt = stmt.order_by(SavedWord.created_at.desc(), SavedWord.id.desc())
    if page is not None:
        stmt = stmt.offset((page - 1) * size).limit(size)
    return list((await db.scalars(stmt)).all()), total


async def saved_items(db, user, rows):
    words = await dictionary.all_by_ids(db, [r.word_id for r in rows])
    descriptions = {
        w.id: d for w, d in zip(words, await dictionary.describe_many(db, words), strict=True)
    }
    sources = await source_map(db, user, list(descriptions))
    for d in descriptions.values():
        d["saved"] = True
    return [
        {
            "id": r.id,
            "word": descriptions[r.word_id],
            "note": r.note,
            "tags": r.tags,
            "created_at": r.created_at,
            "sources": sources.get(r.word_id, []),
        }
        for r in rows
    ]


async def list_saved(db, user, page, size, **filters):
    rows, total = await saved_rows(db, user, page=page, size=size, **filters)
    return {"items": await saved_items(db, user, rows), "total": total, "page": page, "size": size}


async def save_word(db, user, data):
    await require_word(db, user, data.word_id)
    stmt = (
        insert(SavedWord)
        .values(user_id=user.id, **data.model_dump())
        .on_conflict_do_nothing(constraint="uq_saved_user_word")
    )
    await db.execute(stmt)
    row = await db.scalar(
        select(SavedWord).where(SavedWord.user_id == user.id, SavedWord.word_id == data.word_id)
    )
    return (await saved_items(db, user, [row]))[0]


async def get_saved(db, user, saved_id):
    row = await db.scalar(
        select(SavedWord).where(SavedWord.id == saved_id, SavedWord.user_id == user.id)
    )
    if row is None:
        raise AppError(404, "SAVED_WORD_NOT_FOUND", "Không tìm thấy từ đã lưu")
    return row


async def patch_saved(db, user, saved_id, data):
    row = await get_saved(db, user, saved_id)
    await require_word(db, user, row.word_id)
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(row, key, value)
    await db.flush()
    return (await saved_items(db, user, [row]))[0]


async def delete_saved(db, user, saved_id):
    await db.delete(await get_saved(db, user, saved_id))
    await db.flush()
    return {"ok": True}


async def stats(db, user):
    return await dictionary.level_counts(db, saved_query(user).with_only_columns(SavedWord.word_id))


async def collection_item(db, user, row):
    total = await db.scalar(
        select(func.count()).select_from(saved_query(user, collection_id=row.id).subquery())
    )
    return {"id": row.id, "name": row.name, "created_at": row.created_at, "word_count": total}


async def list_collections(db, user, page, size):
    stmt = select(Collection).where(Collection.user_id == user.id)
    total = await db.scalar(select(func.count()).select_from(stmt.subquery()))
    rows = (
        await db.scalars(
            stmt.order_by(Collection.created_at.desc(), Collection.id.desc())
            .offset((page - 1) * size)
            .limit(size)
        )
    ).all()
    # One grouped membership query for the page, avoiding per-collection counts.
    counts = dict(
        (
            await db.execute(
                select(CollectionWord.collection_id, func.count())
                .join(SavedWord, SavedWord.id == CollectionWord.saved_word_id)
                .where(
                    CollectionWord.collection_id.in_([r.id for r in rows]),
                    SavedWord.user_id == user.id,
                    SavedWord.word_id.in_(readable_ids(user)),
                )
                .group_by(CollectionWord.collection_id)
            )
        ).all()
    )
    return {
        "items": [
            {
                "id": r.id,
                "name": r.name,
                "created_at": r.created_at,
                "word_count": counts.get(r.id, 0),
            }
            for r in rows
        ],
        "total": total,
        "page": page,
        "size": size,
    }


async def create_collection(db, user, data):
    stmt = (
        insert(Collection)
        .values(user_id=user.id, name=data.name)
        .on_conflict_do_nothing(constraint="uq_collection_user_name")
        .returning(Collection.id)
    )
    row_id = await db.scalar(stmt)
    if row_id is None:
        raise AppError(409, "COLLECTION_EXISTS", "Tên bộ sưu tập đã tồn tại")
    return await collection_item(db, user, await db.get(Collection, row_id))


async def patch_collection(db, user, collection_id, data):
    row = await get_collection(db, user, collection_id)
    try:
        async with db.begin_nested():
            row.name = data.name
            await db.flush()
    except IntegrityError:
        raise AppError(409, "COLLECTION_EXISTS", "Tên bộ sưu tập đã tồn tại") from None
    return await collection_item(db, user, row)


async def delete_collection(db, user, collection_id):
    await db.delete(await get_collection(db, user, collection_id))
    await db.flush()
    return {"ok": True}


async def collection_members(db, user, collection_id, ids, *, remove=False):
    await get_collection(db, user, collection_id)
    ids = list(dict.fromkeys(ids))
    rows = (
        await db.scalars(
            select(SavedWord).where(
                SavedWord.id.in_(ids),
                SavedWord.user_id == user.id,
                SavedWord.word_id.in_(readable_ids(user)),
            )
        )
    ).all()
    if len(rows) != len(ids):
        raise AppError(404, "SAVED_WORD_NOT_FOUND", "Không tìm thấy từ đã lưu")
    if remove:
        await db.execute(
            delete(CollectionWord).where(
                CollectionWord.collection_id == collection_id, CollectionWord.saved_word_id.in_(ids)
            )
        )
    else:
        await db.execute(
            insert(CollectionWord)
            .values([{"collection_id": collection_id, "saved_word_id": r.id} for r in rows])
            .on_conflict_do_nothing()
        )
    return await collection_item(db, user, await get_collection(db, user, collection_id))
