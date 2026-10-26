"""Export 10 real local words, benchmark 1,000, and roll back all temporary notebook rows."""

import argparse
import asyncio
import csv
import hashlib
import io
import json
import logging
import os
import sqlite3
import statistics
import tempfile
import time
import uuid
import zipfile
from contextlib import closing
from pathlib import Path

import httpx


def verify(content, format, expected):
    if format == "csv":
        assert content.startswith(b"\xef\xbb\xbf")
        assert len(list(csv.DictReader(io.StringIO(content.decode("utf-8-sig"))))) == expected
    elif format == "markdown":
        import yaml

        with zipfile.ZipFile(io.BytesIO(content)) as archive:
            assert len(archive.namelist()) == expected
            for name in archive.namelist():
                front = archive.read(name).decode("utf-8").split("---", 2)[1]
                assert {"word", "reading", "jlpt", "hanviet", "tags", "sources"} <= yaml.safe_load(
                    front
                ).keys()
    else:
        with (
            zipfile.ZipFile(io.BytesIO(content)) as archive,
            tempfile.TemporaryDirectory(prefix="m3-verify-") as directory,
        ):
            assert json.loads(archive.read("media")) == {}
            path = Path(directory) / "notes.sqlite"
            path.write_bytes(archive.read("collection.anki2"))
            with closing(sqlite3.connect(path)) as connection:
                assert connection.execute("SELECT count(*) FROM notes").fetchone()[0] == expected
                assert connection.execute("SELECT count(*) FROM cards").fetchone()[0] == expected


async def measure(args):
    from sqlalchemy import func, insert, select
    from sqlalchemy.dialects.postgresql import insert as upsert

    from app.core.security import token
    from app.db.session import Session, engine, get_db
    from app.main import app
    from app.modules.auth.models import User
    from app.modules.dictionary.models import Word
    from app.modules.notebook.models import Collection, CollectionWord, SavedWord
    from app.modules.textbooks.models import Entry, Lesson, Textbook

    report = {
        "dataset": "1,000 real words from visible local textbook entries",
        "iterations": 3,
        "timing": "ASGI HTTP export including auth, SQL, projection and file rendering; 10-word sample warmup excluded",
    }
    async with Session() as db:
        transaction = await db.begin()
        owner_id = await db.scalar(
            select(Textbook.owner_id)
            .where(func.replace(func.lower(Textbook.name), " ", "").contains("mimikara"))
            .order_by(Textbook.id)
            .limit(1)
        )
        if owner_id is None:
            raise RuntimeError("Real Mimikara source not found")
        user = await db.get(User, owner_id)
        before = await db.scalar(
            select(func.count()).select_from(SavedWord).where(SavedWord.user_id == owner_id)
        )
        query = (
            select(Entry.word_id)
            .join(Lesson, Lesson.id == Entry.lesson_id)
            .join(Textbook, Textbook.id == Lesson.textbook_id)
            .where(Textbook.owner_id == owner_id)
        )
        ids = list(
            (
                await db.scalars(
                    query.where(func.cardinality(Entry.example_lemmas) > 0)
                    .distinct()
                    .order_by(Entry.word_id)
                    .limit(1000)
                )
            ).all()
        )
        if len(ids) < 1000:
            ids += list(
                (
                    await db.scalars(
                        query.where(Entry.word_id.not_in(ids))
                        .distinct()
                        .order_by(Entry.word_id)
                        .limit(1000 - len(ids))
                    )
                ).all()
            )
        if len(ids) != 1000:
            raise RuntimeError("Need 1000 real visible words")
        try:
            await db.execute(
                upsert(SavedWord)
                .values(
                    [
                        {"user_id": owner_id, "word_id": word_id, "note": "", "tags": []}
                        for word_id in ids
                    ]
                )
                .on_conflict_do_nothing(constraint="uq_saved_user_word")
            )
            saved = list(
                (
                    await db.scalars(
                        select(SavedWord).where(
                            SavedWord.user_id == owner_id, SavedWord.word_id.in_(ids)
                        )
                    )
                ).all()
            )
            by_word = {row.word_id: row.id for row in saved}
            sample = Collection(user_id=owner_id, name="__m3_sample_" + uuid.uuid4().hex)
            bulk = Collection(user_id=owner_id, name="__m3_bench_" + uuid.uuid4().hex)
            db.add_all([sample, bulk])
            await db.flush()
            await db.execute(
                insert(CollectionWord),
                [{"collection_id": bulk.id, "saved_word_id": row.id} for row in saved]
                + [
                    {"collection_id": sample.id, "saved_word_id": by_word[word_id]}
                    for word_id in ids[:10]
                ],
            )

            async def dependency():
                yield db

            app.dependency_overrides[get_db] = dependency
            report["sample_words"] = [
                {"id": row.id, "kanji": row.kanji, "kana": row.kana}
                for row in (
                    await db.scalars(select(Word).where(Word.id.in_(ids[:10])).order_by(Word.id))
                ).all()
            ]
            async with httpx.AsyncClient(
                transport=httpx.ASGITransport(app=app),
                base_url="http://measure",
                headers={"Authorization": "Bearer " + token(user.id, "access")[0]},
            ) as client:
                for format, extension in [("anki", "apkg"), ("csv", "csv"), ("markdown", "zip")]:
                    response = await client.get(
                        "/api/v1/saved-words/export",
                        params={"format": format, "collection_id": sample.id},
                    )
                    response.raise_for_status()
                    verify(response.content, format, 10)
                    path = args.output / f"m3-sample-10.{extension}"
                    path.write_bytes(response.content)
                    durations = []
                    for _ in range(3):
                        start = time.perf_counter()
                        response = await client.get(
                            "/api/v1/saved-words/export",
                            params={"format": format, "collection_id": bulk.id},
                        )
                        elapsed = time.perf_counter() - start
                        response.raise_for_status()
                        verify(response.content, format, 1000)
                        durations.append(elapsed)
                    report[format] = {
                        "words": 1000,
                        "samples_seconds": durations,
                        "median_seconds": statistics.median(durations),
                        "max_seconds": max(durations),
                        "bytes": len(response.content),
                        "status": response.status_code,
                        "sample_file": str(path),
                        "sample_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                    }
                    print(format, report[format], flush=True)
        finally:
            app.dependency_overrides.clear()
            await transaction.rollback()
        after = await db.scalar(
            select(func.count()).select_from(SavedWord).where(SavedWord.user_id == owner_id)
        )
        assert before == after
        report["saved_rows_before_after"] = [before, after]
    await engine.dispose()
    return report, owner_id


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path("verification/m3_exports"))
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    os.environ["RATE_LIMIT_ENABLED"] = "false"
    logging.disable(logging.INFO)
    report, owner_id = asyncio.run(measure(args))
    from scripts.measure_m1 import api_rss

    probe = Path("verification/m3")
    probe.mkdir(parents=True, exist_ok=True)
    report["api"] = api_rss(owner_id, probe, 8768)
    (probe / "resources.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (args.output / "README.md").write_text(
        "# M3 sample exports\n\n10 real words from the local textbook DB; OCR content needs source review.\n\n- m3-sample-10.apkg: import in Anki.\n- m3-sample-10.csv: UTF-8 BOM, open in Excel.\n- m3-sample-10.zip: unzip into an Obsidian vault.\n\nNo media or new furigana. Temporary saved words/collections were rolled back.\n",
        encoding="utf-8",
    )
    print("RSS bytes:", report["api"]["rss_bytes"])
    assert all(report[format]["max_seconds"] < 10 for format in ["anki", "csv", "markdown"])


if __name__ == "__main__":
    main()
