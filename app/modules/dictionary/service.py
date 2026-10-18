import asyncio
import csv
import io
import json
from pathlib import Path

from sqlalchemy import func, or_, select
from sqlalchemy.dialects.postgresql import insert

from app.core.exceptions import AppError
from app.nlp.kanji import breakdown
from app.nlp.normalize import kana_normalize, to_romaji

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
