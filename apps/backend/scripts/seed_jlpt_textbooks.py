"""Seed OpenJLPT vocab-n{1..5}.csv from data/ using an existing admin account.

Offline only. Source order, 50 rows per lesson; repeated runs update matching entries.
"""

import argparse
import asyncio
import csv
import hashlib
from pathlib import Path

from sqlalchemy import select, text

from app.db.session import Session
from app.modules.auth.models import User
from app.modules.auth.service import require_admin
from app.modules.dictionary import service as dictionary
from app.modules.textbooks import service as textbooks
from app.modules.textbooks.models import Textbook
from app.modules.textbooks.schemas import TextbookCreate
from app.nlp.normalize import kana_normalize

SOURCE = "https://github.com/evanclan/OpenJLPT"
LICENSE = "CC BY-SA 4.0 — OpenJLPT; JMdict/EDRDG; Jonathan Waller JLPT lists (CC BY)"


async def seed(db, user, directory):
    require_admin(user)
    await db.execute(text("SELECT pg_advisory_xact_lock(1312968772)"))
    inputs = []
    for level in range(5, 0, -1):
        path = Path(directory) / f"vocab-n{level}.csv"
        with path.open(encoding="utf-8-sig", newline="") as handle:
            rows = list(csv.DictReader(handle))
        if not rows or any(
            not row.get("word")
            or not kana_normalize(row.get("reading", ""))
            or not row.get("meanings")
            or row.get("level") != f"N{level}"
            for row in rows
        ):
            raise ValueError(f"Invalid or empty OpenJLPT CSV: {path}")
        inputs.append((level, path, rows))
    report = []
    for level, path, rows in inputs:
        url = f"{SOURCE}/blob/main/data/csv/vocab-n{level}.csv"
        books = (await db.scalars(select(Textbook).where(Textbook.source_url == url))).all()
        if len(books) > 1 or any(b.owner_id != user.id for b in books):
            raise ValueError("Source already seeded by another owner or duplicated")
        book = (
            books[0]
            if books
            else await textbooks.create_textbook(
                db,
                user,
                TextbookCreate(
                    name=f"JLPT N{level}",
                    level=f"N{level}",
                    visibility="public",
                    license=LICENSE,
                    source_url=url,
                ),
            )
        )
        seen = set()
        duplicates = 0
        for index, row in enumerate(rows):
            spelling, reading = row["word"], row["reading"]
            kanji = "" if spelling == reading else spelling
            candidates = await dictionary.match(db, kanji, reading)
            exact = [
                w for w in candidates if w.kanji == kanji and w.kana_norm == kana_normalize(reading)
            ]
            word = exact[0] if exact else await dictionary.create_word(db, kanji, reading)
            lesson = await textbooks.ensure_lesson(db, user, book.id, index // 50 + 1)
            if (lesson.id, word.id) in seen:
                duplicates += 1
                continue
            seen.add((lesson.id, word.id))
            await textbooks.save_entry(
                db,
                user,
                lesson.id,
                word.id,
                index % 50 + 1,
                [{"type": "meaning", "en": row["meanings"]}],
            )
        report.append(
            {
                "level": level,
                "rows": len(rows),
                "entries": len(seen),
                "duplicates_in_lesson": duplicates,
                "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                "textbook_id": book.id,
            }
        )
    return report


async def main(args):
    async with Session.begin() as db:
        user = await db.scalar(select(User).where(User.email == args.admin_email.lower()))
        if user is None:
            raise ValueError("Register an admin account first")
        print(await seed(db, user, args.directory))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--admin-email", required=True)
    parser.add_argument("--directory", type=Path, default=Path("data/openjlpt"))
    asyncio.run(main(parser.parse_args()))
