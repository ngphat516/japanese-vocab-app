import asyncio
import csv
import io
import json
import unicodedata
from pathlib import Path

from sqlalchemy import and_, func, literal, or_, select, text, union_all
from sqlalchemy.dialects.postgresql import insert

from app.core.exceptions import AppError
from app.nlp.kanji import breakdown
from app.nlp.normalize import is_vietnamese, kana_normalize, to_romaji

from .models import Kanji, Word, WordSense


async def kanji_breakdown(db, text):
    chars = list(dict.fromkeys(c for c in text if "一" <= c <= "鿿"))
    rows = {r.char: r for r in (await db.scalars(select(Kanji).where(Kanji.char.in_(chars)))).all()}
    return breakdown(text, {char: row.hanviet for char, row in rows.items()})


async def create_word(db, kanji, kana, **extra):
    breakdown = await kanji_breakdown(db, kanji)
    word = Word(
        kanji=kanji,
        kana=kana,
        kana_norm=kana_normalize(kana),
        romaji=to_romaji(kana),
        hanviet=" ".join(x["hanviet"] for x in breakdown if x["hanviet"]),
        **extra,
    )
    db.add(word)
    await db.flush()
    return word


async def match(db, kanji, kana):
    statement = select(Word).where(Word.kana_norm == kana_normalize(kana))
    if kanji:
        statement = statement.where(Word.kanji == kanji)
    return list((await db.scalars(statement.order_by(Word.id))).all())


async def get_word(db, word_id):
    word = await db.get(Word, word_id)
    if not word:
        raise AppError(404, "WORD_NOT_FOUND", "Không tìm thấy từ")
    return word


async def describe(db, word):
    return {
        "id": word.id,
        "kanji": word.kanji,
        "kana": word.kana,
        "romaji": word.romaji,
        "hanviet": word.hanviet,
        "jlpt_level": word.jlpt_level,
        "kanji_breakdown": await kanji_breakdown(db, word.kanji),
        "saved": False,
    }


async def describe_many(db, words):
    chars = {c for word in words for c in word.kanji if "一" <= c <= "鿿"}
    readings = {
        row.char: row.hanviet
        for row in (await db.scalars(select(Kanji).where(Kanji.char.in_(chars)))).all()
    }
    return [
        {
            "id": word.id,
            "kanji": word.kanji,
            "kana": word.kana,
            "romaji": word.romaji,
            "hanviet": word.hanviet,
            "jlpt_level": word.jlpt_level,
            "kanji_breakdown": breakdown(word.kanji, readings),
            "saved": False,
        }
        for word in words
    ]


async def senses(db, word_id):
    return [
        {"lang": x.lang, "gloss": x.gloss, "order": x.order}
        for x in (
            await db.scalars(
                select(WordSense)
                .where(WordSense.word_id == word_id)
                .order_by(WordSense.order, WordSense.id)
            )
        ).all()
    ]


async def search_candidates(db, query, normalized, kind, jlpt):
    # Expose a read service boundary; search never imports dictionary models.
    exact = or_(Word.kanji == query, Word.kana_norm == normalized)
    prefix = or_(
        Word.kanji.startswith(query, autoescape=True),
        Word.kana_norm.startswith(normalized, autoescape=True),
    )
    meaning = select(WordSense.word_id).where(
        or_(
            WordSense.gloss.ilike(
                "%" + query.replace("%", r"\%").replace("_", r"\_") + "%", escape="\\"
            ),
            func.similarity(WordSense.gloss, query) >= 0.3,
        )
    )
    stmt = select(Word).where(or_(exact, prefix, Word.id.in_(meaning)))
    if jlpt:
        stmt = stmt.where(Word.jlpt_level == jlpt)
    words = list((await db.scalars(stmt)).all())

    def rank(w):
        return (
            0
            if w.kanji == query or w.kana_norm == normalized
            else 1
            if w.kanji.startswith(query) or w.kana_norm.startswith(normalized)
            else 2,
            w.id,
        )

    return sorted(words, key=rank)


async def all_by_ids(db, ids):
    return list((await db.scalars(select(Word).where(Word.id.in_(ids)))).all())


def word_id_equals(word_id):
    return Word.id == word_id


def readable_ids(entry_ids, jlpt=None, *, require_entry=False):
    stmt = select(Word.id).where(
        Word.id.in_(entry_ids)
        if require_entry
        else or_(Word.jmdict_id.is_not(None), Word.id.in_(entry_ids))
    )
    if jlpt:
        stmt = stmt.where(Word.jlpt_level.is_(None) if jlpt == "none" else Word.jlpt_level == jlpt)
    return stmt


async def level_counts(db, word_ids):
    rows = (
        await db.execute(
            select(Word.jlpt_level, func.count())
            .where(Word.id.in_(word_ids))
            .group_by(Word.jlpt_level)
        )
    ).all()
    result = dict.fromkeys(["N1", "N2", "N3", "N4", "N5", "none"], 0)
    result.update({level or "none": count for level, count in rows})
    return result


async def senses_many(db, word_ids):
    result = {}
    rows = (
        await db.scalars(
            select(WordSense)
            .where(WordSense.word_id.in_(word_ids))
            .order_by(WordSense.word_id, WordSense.order, WordSense.id)
        )
    ).all()
    for row in rows:
        result.setdefault(row.word_id, []).append({"lang": row.lang, "gloss": row.gloss})
    return result


def substring_condition(column, query):
    escaped = query.replace("\\", "\\\\").replace("%", r"\%").replace("_", r"\_")
    pattern = "%" + escaped + "%"
    if query.lower() == query.upper():
        if len(query) < 3:
            # A one/two-character substring has no selective internal trigram.
            # Literal strpos avoids a GIN walk that rechecks the entire index.
            return func.strpos(column, query) > 0
        return column.like(pattern, escape="\\")
    if len(query) == 1 and query.isascii() and query.isalpha():
        return or_(column.like(pattern.lower()), column.like(pattern.upper()))
    return column.ilike(pattern, escape="\\")


def short_latin(query):
    return 0 < len(query) < 3 and all("LATIN" in unicodedata.name(c, "") for c in query)


def prefix_condition(column, query):
    # Explicit pattern-order bounds remain indexable even in a generic prepared
    # plan, where PostgreSQL cannot derive bounds from a parameterized LIKE.
    trimmed = query.rstrip(chr(0x10FFFF))
    clauses = [column.bool_op("~>=~")(query), column.startswith(query, autoescape=True)]
    if trimmed:
        upper = trimmed[:-1] + chr(ord(trimmed[-1]) + 1)
        clauses.append(column.bool_op("~<~")(upper))
    return and_(*clauses)


def meaning_condition(column, query):
    # Short Latin searches match the beginning of the gloss, case-insensitively.
    if short_latin(query):
        return prefix_condition(func.lower(column), query.lower())
    return substring_condition(column, query)


def text_match_condition(column, query):
    substring = meaning_condition(column, query)
    if len(query) <= 2 and query.isalnum():
        return substring
    return or_(substring, column.bool_op("%")(query))


def search_sources(query, normalized, jlpt, entry_matches, visible_ids, lemma_forms=()):
    exact = or_(Word.kanji == query, Word.kana_norm == normalized)
    prefix = or_(
        prefix_condition(Word.kanji, query),
        prefix_condition(Word.kana_norm, normalized),
    )
    sources = [
        (select(Word.id.label("word_id")).where(exact), 0),
        (select(Word.id.label("word_id")).where(prefix), 2),
        (
            select(WordSense.word_id).where(meaning_condition(WordSense.gloss, query)),
            3,
        ),
    ]
    if lemma_forms:
        sources.append(
            (
                select(Word.id.label("word_id")).where(
                    or_(Word.kanji.in_(lemma_forms), Word.kana_norm.in_(lemma_forms))
                ),
                1,
            )
        )
    # For one/two alphanumeric characters, similarity >= .3 implies substring:
    # sharing only the padded first-character trigram scores at most 1/4.
    if len(query) > 2 or not query.isalnum():
        sources.append((select(WordSense.word_id).where(WordSense.gloss.bool_op("%")(query)), 3))
    sources.append((entry_matches, 3))
    if is_vietnamese(query):
        vie = (
            select(WordSense.word_id, WordSense.gloss)
            .where(WordSense.lang == "vie")
            .cte("vietnamese_senses")
            .prefix_with("MATERIALIZED")
        )
        sources = [
            (
                select(vie.c.word_id).where(text_match_condition(vie.c.gloss, query)),
                3,
            ),
            (entry_matches, 3),
        ]
    filtered = []
    for stmt, rank in sources:
        column = stmt.selected_columns[0]
        if jlpt:
            stmt = stmt.where(column.in_(select(Word.id).where(Word.jlpt_level == jlpt)))
        if visible_ids is not None:
            stmt = stmt.where(column.in_(visible_ids))
        filtered.append((stmt, rank))
    return filtered


async def search_page(
    db, query, normalized, jlpt, entry_matches, visible_ids, page, size, lemma_forms=()
):
    await db.execute(text("SET LOCAL work_mem = '16MB'"))
    sources = search_sources(query, normalized, jlpt, entry_matches, visible_ids, lemma_forms)
    # Filter text sources before DISTINCT/ORDER/LIMIT. Otherwise a generic plan
    # can walk the entire word_id index looking for a handful of text matches.
    prepared_sources = []
    for index, (stmt, rank) in enumerate(sources):
        if rank >= 3:
            filtered = stmt.cte(f"search_source_{index}").prefix_with("MATERIALIZED")
            stmt = select(filtered.c.word_id)
        prepared_sources.append((stmt, rank))
    sources = prepared_sources
    # At most 1001 distinct IDs per source and 1001 in the final union. The extra
    # ID distinguishes exactly 1000 matches from a capped lower bound.
    count_sources = [
        select(source.c.word_id)
        for stmt, rank in sources
        for source in [(stmt.distinct() if rank >= 3 else stmt).limit(1001).subquery()]
    ]
    count_ids = union_all(*count_sources).subquery()
    count_sample = select(count_ids.c.word_id).distinct().limit(1001).subquery()
    observed = await db.scalar(select(func.count()).select_from(count_sample))
    # A global top K cannot need more than K distinct IDs from any ranked source.
    # Apply the same filters before these bounds so sparse filtered pages stay full.
    bounded = []
    for stmt, rank in sources:
        column = stmt.selected_columns[0]
        if rank < 3:
            # Word IDs are already unique. Sort the filtered matches instead of
            # walking the PK index in ID order and discarding nonmatching rows.
            stmt = stmt.order_by(column + 0)
        else:
            stmt = stmt.distinct().order_by(column)
        source = stmt.limit(page * size).subquery()
        bounded.append(select(source.c.word_id, literal(rank).label("rank")))
    candidates = union_all(*bounded).subquery()
    ranked = (
        select(candidates.c.word_id, func.min(candidates.c.rank).label("rank"))
        .group_by(candidates.c.word_id)
        .subquery()
    )
    paged = (
        select(ranked)
        .order_by(ranked.c.rank, ranked.c.word_id)
        .offset((page - 1) * size)
        .limit(size)
        .subquery()
    )
    words = list(
        (
            await db.scalars(
                select(Word).join(paged, paged.c.word_id == Word.id).order_by(paged.c.rank, Word.id)
            )
        ).all()
    )
    return words, min(observed, 1000), observed > 1000


async def seed_jmdict(db, path):
    document = json.loads(await asyncio.to_thread(Path(path).read_text, encoding="utf-8-sig"))
    for row in document.get("words", []):
        readings = row.get("kana", [])
        for reading in readings:
            kana = reading["text"]
            spellings = [
                x["text"]
                for x in row.get("kanji", [])
                if reading.get("appliesToKanji", ["*"]) == ["*"]
                or x["text"] in reading.get("appliesToKanji", [])
            ] or [""]
            for kanji in spellings:
                found = await match(db, kanji, kana)
                word = next((w for w in found if w.kanji == kanji and w.kana == kana), None)
                if not word:
                    word = await create_word(
                        db,
                        kanji,
                        kana,
                        jmdict_id=str(row["id"]),
                        pos=list(
                            dict.fromkeys(
                                p for s in row.get("sense", []) for p in s.get("partOfSpeech", [])
                            )
                        ),
                    )
                for index, sense in enumerate(row.get("sense", [])):
                    if (
                        kanji
                        and sense.get("appliesToKanji", ["*"]) != ["*"]
                        and kanji not in sense["appliesToKanji"]
                    ):
                        continue
                    if (
                        sense.get("appliesToKana", ["*"]) != ["*"]
                        and kana not in sense["appliesToKana"]
                    ):
                        continue
                    for gloss in sense.get("gloss", []):
                        lang, text = gloss.get("lang", "eng"), gloss["text"]
                        exists = await db.scalar(
                            select(WordSense.id).where(
                                WordSense.word_id == word.id,
                                WordSense.lang == lang,
                                WordSense.gloss == text,
                                WordSense.order == index,
                            )
                        )
                        if not exists:
                            db.add(WordSense(word_id=word.id, lang=lang, gloss=text, order=index))
                await db.flush()


async def seed_kanjidic(db, path):
    document = json.loads(await asyncio.to_thread(Path(path).read_text, encoding="utf-8-sig"))
    for row in document.get("characters", []):
        char = row.get("literal") or row.get("char")
        meaning = row.get("meaning", "")
        if not meaning:
            groups = (row.get("readingMeaning") or {}).get("groups", [])
            meaning = "; ".join(
                m["value"]
                for g in groups
                for m in g.get("meanings", [])
                if m.get("lang", "en") == "en"
            )
        strokes = row.get("strokes") or next(
            iter(row.get("misc", {}).get("strokeCounts", [])), None
        )
        stmt = insert(Kanji).values(char=char, meaning=meaning, strokes=strokes, hanviet=[])
        await db.execute(
            stmt.on_conflict_do_update(
                index_elements=["char"], set_={"meaning": meaning, "strokes": strokes}
            )
        )


async def seed_hanviet(db, path):
    text = await asyncio.to_thread(Path(path).read_text, encoding="utf-8-sig")
    for row in csv.DictReader(io.StringIO(text)):
        values = [x.strip() for x in row["hanviet"].split("|") if x.strip()]
        stmt = insert(Kanji).values(char=row["kanji"], hanviet=values, meaning="")
        await db.execute(
            stmt.on_conflict_do_update(index_elements=["char"], set_={"hanviet": values})
        )
    for word in (await db.scalars(select(Word))).all():
        word.hanviet = " ".join(
            x["hanviet"] for x in await kanji_breakdown(db, word.kanji) if x["hanviet"]
        )


async def seed_jlpt(db, path):
    text = await asyncio.to_thread(Path(path).read_text, encoding="utf-8-sig")
    for row in csv.DictReader(io.StringIO(text)):
        if row["jlpt_level"] not in {"N1", "N2", "N3", "N4", "N5"}:
            raise ValueError("JLPT level invalid")
        for word in await match(db, row["kanji"], row["kana"]):
            word.jlpt_level = row["jlpt_level"]
    await db.flush()
