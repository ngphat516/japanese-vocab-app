import json

from app.core.exceptions import AppError
from app.modules.dictionary import service as dictionary
from app.modules.textbooks import service as textbooks
from app.nlp.normalize import normalize_query, query_type


def public_entry(entry, full=True):
    return {k: (v if full or k != "content" else None) for k, v in entry.items() if k != "word_id"}


async def search(db, user, query, textbook_ids, jlpt, page, size):
    query = query.strip()
    if not query:
        raise AppError(422, "EMPTY_QUERY", "Truy vấn không được rỗng")
    normalized = normalize_query(query)
    if query_type(query) == "kanji":
        query = normalized
    words = await dictionary.search_candidates(db, query, normalized, query_type(query), jlpt)
    meaning_entries = await textbooks.visible_entries(
        db, user, textbook_ids=textbook_ids, query=query
    )
    existing = {w.id for w in words}
    extras = await dictionary.all_by_ids(db, {e["word_id"] for e in meaning_entries} - existing)
    words.extend(
        sorted((w for w in extras if not jlpt or w.jlpt_level == jlpt), key=lambda w: w.id)
    )
    entries = await textbooks.visible_entries(
        db, user, word_ids=[w.id for w in words], textbook_ids=textbook_ids
    )
    by_word = {}
    for entry in entries:
        by_word.setdefault(entry["word_id"], []).append(entry)
    if textbook_ids:
        words = [w for w in words if w.id in by_word]
    total = len(words)
    start = (page - 1) * size
    result = {
        "items": [
            {
                "word": await dictionary.describe(db, w),
                "entries": [public_entry(e, start + index < 10) for e in by_word.get(w.id, [])],
            }
            for index, w in enumerate(words[start : start + size])
        ],
        "page": page,
        "size": size,
        "total": total,
    }
    if len(json.dumps(result, ensure_ascii=False).encode("utf-8")) > 195000:
        raise AppError(
            422, "SEARCH_PAGE_TOO_LARGE", "Trang vượt 200 KB, hãy giảm size hoặc lọc giáo trình"
        )
    return result


async def word_detail(db, user, word_id):
    word = await dictionary.get_word(db, word_id)
    return {
        "word": await dictionary.describe(db, word),
        "senses": await dictionary.senses(db, word_id),
        "entries": [public_entry(e) for e in await textbooks.visible_entries(db, user, [word_id])],
    }
