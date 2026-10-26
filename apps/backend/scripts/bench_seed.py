"""Bulk projection of full jmdict-simplified into an empty benchmark database.

All entries/readings/spellings are traversed, respecting appliesTo restrictions.
COPY only changes the loading method; it does not invent meanings or JLPT labels.
"""

import asyncio
import hashlib
import json
from pathlib import Path

from app.nlp.normalize import kana_normalize, to_romaji
from app.nlp.tokenizer import entry_lemmas


def project(path):
    document = json.loads(Path(path).read_text(encoding="utf-8-sig"))
    words, senses, pairs, seen_senses = [], [], {}, set()
    for row in document["words"]:
        for reading in row["kana"]:
            kana = reading["text"]
            spellings = [
                x["text"]
                for x in row["kanji"]
                if reading["appliesToKanji"] == ["*"] or x["text"] in reading["appliesToKanji"]
            ] or [""]
            for kanji in spellings:
                key = kanji, kana
                if key not in pairs:
                    pairs[key] = word_id = len(words) + 1
                    words.append(
                        (
                            word_id,
                            str(row["id"]),
                            kanji,
                            kana,
                            kana_normalize(kana),
                            to_romaji(kana),
                            "",
                            list(
                                dict.fromkeys(
                                    p for sense in row["sense"] for p in sense["partOfSpeech"]
                                )
                            ),
                        )
                    )
                word_id = pairs[key]
                for order, sense in enumerate(row["sense"]):
                    if (
                        kanji
                        and sense["appliesToKanji"] != ["*"]
                        and kanji not in sense["appliesToKanji"]
                    ):
                        continue
                    if sense["appliesToKana"] != ["*"] and kana not in sense["appliesToKana"]:
                        continue
                    for gloss in sense["gloss"]:
                        record = word_id, gloss["lang"], gloss["text"], order
                        if record not in seen_senses:
                            seen_senses.add(record)
                            senses.append(record)
    return (
        words,
        senses,
        {
            "dataset": "jmdict-simplified-full-eng",
            "source": "https://github.com/scriptin/jmdict-simplified",
            "source_file": Path(path).name,
            "sha256": hashlib.sha256(Path(path).read_bytes()).hexdigest(),
            "source_entries": len(document["words"]),
            "dict_date": document.get("dictDate"),
            "common_only": document.get("commonOnly"),
            "words": len(words),
            "senses": len(senses),
            "entries": 0,
            "license": "CC-BY-SA-4.0; JMdict/EDRDG attribution in source distribution",
        },
    )


async def seed_full_jmdict(db, path):
    words, senses, metadata = await asyncio.to_thread(project, path)
    raw = await db.get_raw_connection()
    conn = raw.driver_connection
    await conn.copy_records_to_table(
        "words",
        records=words,
        columns=[
            "id",
            "jmdict_id",
            "kanji",
            "kana",
            "kana_norm",
            "romaji",
            "hanviet",
            "pos",
        ],
    )
    await conn.copy_records_to_table(
        "word_senses",
        records=senses,
        columns=[
            "word_id",
            "lang",
            "gloss",
            "order",
        ],
    )
    print(json.dumps(metadata, ensure_ascii=True), flush=True)
    return metadata


async def seed_examples(db):
    """Same 12,000 textbook entries in both benchmark scenarios, with real NLP."""
    from sqlalchemy import text

    await db.execute(
        text(
            "INSERT INTO textbooks(id,name,visibility,owner_id) VALUES (1,'Benchmark','private',1)"
        )
    )
    await db.execute(
        text("INSERT INTO lessons(id,textbook_id,number,title) VALUES (1,1,1,'Benchmark lesson')")
    )
    ids = list((await db.execute(text("SELECT id FROM words ORDER BY id LIMIT 12000"))).scalars())
    contents = [
        [{"type": "meaning", "en": "invented benchmark"}, {"type": "example", "ja": sentence}]
        for sentence in ["猫が部屋にいる。", "学校へ行かなかった。", "学校で緊張している。"]
    ]
    arrays = await asyncio.to_thread(lambda: [entry_lemmas(c) for c in contents])
    records = []
    for n, word_id in enumerate(ids, 1):
        index = 2 if n % 101 == 0 else 1 if n % 97 == 0 else 0
        records.append(
            (
                word_id,
                1,
                n,
                json.dumps(contents[index], ensure_ascii=False),
                ("căng thẳng " if n == 1 else "invented benchmark ") + contents[index][1]["ja"],
                arrays[index],
            )
        )
    raw = await db.get_raw_connection()
    await raw.driver_connection.copy_records_to_table(
        "textbook_entries",
        records=records,
        columns=["word_id", "lesson_id", "order_no", "content", "search_text", "lemmas"],
    )
    return len(records)
