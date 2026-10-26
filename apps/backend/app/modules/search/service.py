import asyncio
import json

from app.core.exceptions import AppError
from app.modules.dictionary import service as dictionary
from app.modules.textbooks import service as textbooks
from app.nlp.normalize import is_vietnamese, normalize_query, query_type
from app.nlp.tokenizer import FORMAL_NOUNS, lemmas


def query_lemmas(query):
    kind = query_type(query)
    if is_vietnamese(query) or (
        kind != "kanji" and not (kind == "kana" and len(query.replace(" ", "")) >= 3)
    ):
        return []
    forms = [value for value in lemmas(query) if value not in FORMAL_NOUNS]
    if set(forms) - {"する", "為る"}:
        forms = [value for value in forms if value not in {"する", "為る"}]
    return forms


def matched_by(word, query, normalized, forms):
    if word.kanji == query or word.kana_norm == normalized:
        return "exact"
    if word.kanji in forms or word.kana_norm in forms:
        return "lemma"
    if word.kanji.startswith(query) or word.kana_norm.startswith(normalized):
        return "prefix"
    return "meaning"


def public_entry(entry, full=True):
    return {k: (v if full or k != "content" else None) for k, v in entry.items() if k != "word_id"}


async def search(db, user, query, textbook_ids, jlpt, page, size):
    query = query.strip()
    if not query:
        raise AppError(422, "EMPTY_QUERY", "Truy vấn không được rỗng")
    normalized = normalize_query(query)
    if query_type(query) == "kanji":
        query = normalized
    forms = await asyncio.to_thread(query_lemmas, query)
    words, total, total_capped = await dictionary.search_page(
        db,
        query,
        normalized,
        jlpt,
        textbooks.visible_word_ids(user, textbook_ids, query),
        textbooks.visible_word_ids(user, textbook_ids) if textbook_ids else None,
        page,
        size,
        forms,
    )
    entries = await textbooks.visible_entries(
        db, user, word_ids=[w.id for w in words], textbook_ids=textbook_ids
    )
    by_word = {}
    for entry in entries:
        by_word.setdefault(entry["word_id"], []).append(entry)
    start = (page - 1) * size
    descriptions = await dictionary.describe_many(db, words)
    counts = await textbooks.example_counts(db, user, descriptions[: max(0, 10 - start)])
    result = {
        "items": [
            {
                "word": description,
                "entries": [public_entry(e, start + index < 10) for e in by_word.get(w.id, [])],
                "matched_by": matched_by(w, query, normalized, forms),
                "appears_in_examples": counts.get(w.id),
            }
            for index, (w, description) in enumerate(zip(words, descriptions, strict=True))
        ],
        "page": page,
        "size": size,
        "total": total,
        "total_capped": total_capped,
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


async def word_examples(db, user, word_id, page, size):
    word = await dictionary.get_word(db, word_id)
    return await textbooks.word_examples(db, user, await dictionary.describe(db, word), page, size)
