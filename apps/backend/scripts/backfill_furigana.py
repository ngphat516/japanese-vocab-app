"""Backfill only derived furigana; backup before running. Keyset batches and CAS."""

import argparse
import asyncio

from sqlalchemy import select, update

from app.db.session import Session
from app.modules.dictionary import service as dictionary
from app.modules.textbooks.models import Entry, Lesson
from app.modules.textbooks.service import textbook_readings
from app.nlp.furigana import content_furigana


async def backfill(sessions=Session, *, dry_run=False, batch_size=500):
    changed = scanned = last_id = 0
    while True:
        async with sessions() as db, db.begin():
            rows = (
                await db.execute(
                    select(Entry, Lesson.textbook_id)
                    .join(Lesson, Entry.lesson_id == Lesson.id)
                    .where(Entry.id > last_id)
                    .order_by(Entry.id)
                    .limit(batch_size)
                )
            ).all()
            if not rows:
                break
            maps = {
                book_id: await textbook_readings(db, book_id) for book_id in {r[1] for r in rows}
            }
            words = {w.id: w for w in await dictionary.all_by_ids(db, [e.word_id for e, _ in rows])}
            for entry, book_id in rows:
                word = words[entry.word_id]
                readings = {**maps[book_id], **({word.kanji: word.kana} if word.kanji else {})}
                value = (
                    await asyncio.to_thread(content_furigana, entry.content, readings)
                    if entry.auto_furigana
                    else None
                )
                if value != entry.content_furigana:
                    changed += 1
                    if not dry_run:
                        previous = (
                            Entry.content_furigana.is_(None)
                            if entry.content_furigana is None
                            else Entry.content_furigana == entry.content_furigana
                        )
                        result = await db.execute(
                            update(Entry)
                            .where(
                                Entry.id == entry.id,
                                Entry.content == entry.content,
                                Entry.auto_furigana == entry.auto_furigana,
                                previous,
                            )
                            .values(content_furigana=value)
                            .execution_options(synchronize_session=False)
                        )
                        if result.rowcount != 1:
                            raise RuntimeError(f"Entry {entry.id} changed concurrently; rerun")
            scanned += len(rows)
            last_id = rows[-1][0].id
    return {"scanned": scanned, "changed": changed, "dry_run": dry_run}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true")
    print(asyncio.run(backfill(dry_run=parser.parse_args().dry_run)))
