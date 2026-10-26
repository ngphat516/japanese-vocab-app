import asyncio
import os
import subprocess

from alembic.config import Config
from alembic.script import ScriptDirectory
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.modules.dictionary import service as dictionary
from app.modules.textbooks import service
from app.modules.textbooks.models import Entry
from app.nlp.furigana import search_text
from scripts.backfill_lemmas import backfill


async def test_save_entry_keeps_summary_and_stores_lemmas(imported, db):
    from app.modules.auth.service import current_user

    client, book, _ = imported
    user = await current_user(db, client.headers["authorization"][7:])
    lesson = await service.ensure_lesson(db, user, book["id"], 99)
    word = await dictionary.create_word(db, "検証", "けんしょう")
    content = [{"type": "example", "ja": "{{行[い]かなかった}}"}]
    entry = await service.save_entry(db, user, lesson.id, word.id, 1, content)
    assert entry.lemmas == ["行く", "いく"]
    assert entry.search_text == search_text(content) == "行かなかった"
    result = (await client.get("/api/v1/search", params={"q": "検証"})).json()
    assert result["items"][0]["entries"][0]["summary"] == "行かなかった"
    await service.save_entry(
        db, user, lesson.id, word.id, 1, [{"type": "example", "ja": "食べました"}]
    )
    assert entry.lemmas == ["食べる", "たべる"]


async def test_backfill_dry_run_and_idempotence(imported, db):
    # Bind fresh sessions to the fixture's transaction/savepoints, not a live DB.
    sessions = async_sessionmaker(
        bind=await db.connection(), expire_on_commit=False, join_transaction_mode="create_savepoint"
    )
    await db.execute(text("UPDATE textbook_entries SET lemmas='{}'"))
    before = (
        await db.execute(select(Entry.id, Entry.content, Entry.search_text).order_by(Entry.id))
    ).all()
    dry = await backfill(sessions, dry_run=True, batch_size=1)
    assert dry["changed"] > 0
    assert all(not v for v in (await db.scalars(select(Entry.lemmas))).all())
    first = await backfill(sessions, batch_size=1)
    assert first["changed"] == dry["changed"]
    assert (await backfill(sessions, batch_size=1))["changed"] == 0
    assert (
        await db.execute(select(Entry.id, Entry.content, Entry.search_text).order_by(Entry.id))
    ).all() == before


async def test_0003_upgrade_downgrade_upgrade(pg_url):
    # pg_url belongs to this suite's Testcontainers instance. Never run against local data.
    env = {**os.environ, "DATABASE_URL": pg_url}
    engine = create_async_engine(pg_url)
    try:
        for target in ["0002_meaning_prefix", "head"]:
            direction = "downgrade" if target == "0002_meaning_prefix" else "upgrade"
            await asyncio.to_thread(
                subprocess.run,
                [os.sys.executable, "-m", "alembic", direction, target],
                env=env,
                check=True,
                capture_output=True,
            )
        async with engine.connect() as connection:
            assert (
                await connection.scalar(text("SELECT version_num FROM alembic_version"))
                == ScriptDirectory.from_config(Config("alembic.ini")).get_current_head()
            )
            assert (
                await connection.scalar(
                    text("SELECT count(*) FROM pg_indexes WHERE indexname='ix_entries_lemmas'")
                )
                == 1
            )
            assert (
                await connection.scalar(
                    text(
                        "SELECT column_default FROM information_schema.columns WHERE table_name='textbook_entries' AND column_name='lemmas'"
                    )
                )
                == "'{}'::text[]"
            )
    finally:
        await engine.dispose()
