import json

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.modules.auth.service import current_user
from app.modules.dictionary import service as dictionary
from app.modules.textbooks import service
from app.modules.textbooks.models import Entry
from app.nlp.furigana import add_furigana, content_furigana
from scripts.backfill_furigana import backfill


def test_target_override_private_and_idempotence():
    assert add_furigana("{{協力}}") == "{{協力[きょうりょく]}}"
    assert add_furigana("{{緊張して}}") == "{{緊張[きんちょう]して}}"
    assert add_furigana("{{腹痛}}", {"腹痛": "ふくつう"}) == "{{腹痛[ふくつう]}}"
    assert add_furigana("私") == "私[わたし]"
    assert (
        "腹痛"
        not in __import__("app.nlp.furigana", fromlist=["READING_OVERRIDES"]).READING_OVERRIDES
    )
    assert add_furigana("腹痛", {"腹痛": "はらいた"}) == "腹痛[はらいた]"
    original = "では{{緊張[きんちょう]して}}私[わたくし]"
    assert add_furigana(original) == original
    blocks = [
        {"type": "usage", "context": "私", "variants": [{"ja": "協力", "correct": True}]},
        {"type": "collocation", "items": ["私"]},
    ]
    derived = content_furigana(blocks, {})
    assert derived[0]["context"] == "私[わたし]" and blocks[0]["context"] == "私"
    assert content_furigana(derived, {}) == derived


async def test_same_textbook_reading_and_raw_search(imported, db):
    client, book, _ = imported
    user = await current_user(db, client.headers["authorization"][7:])
    lesson = await service.ensure_lesson(db, user, book["id"], 88)
    target = await dictionary.create_word(db, "腹痛", "はらいた")
    await service.save_entry(
        db, user, lesson.id, target.id, 1, [{"type": "meaning", "en": "stomachache"}]
    )
    source = await dictionary.create_word(db, "症状", "しょうじょう")
    blocks = [{"type": "example", "ja": "腹痛がある。"}]
    entry = await service.save_entry(db, user, lesson.id, source.id, 2, blocks)
    assert entry.content_furigana[0]["ja"] == "腹痛[はらいた]がある。"
    detail = (await client.get(f"/api/v1/words/{source.id}?furigana=false")).json()
    assert detail["entries"][0]["content"][0]["ja"] == blocks[0]["ja"]
    search = (await client.get("/api/v1/search?q=症状&furigana=false")).json()
    assert search["items"][0]["entries"][0]["content"][0]["ja"] == blocks[0]["ja"]
    examples = (await client.get(f"/api/v1/words/{target.id}/examples")).json()
    assert examples["items"][0]["sentences"][0]["ja"] == "腹痛[はらいた]がある。"


async def test_import_auto_furigana_off(authorized, seeded, db):
    from tests.conftest import FIXTURES

    client, _ = authorized
    book = (await client.post("/api/v1/textbooks", json={"name": "No auto"})).json()
    response = await client.post(
        "/api/v1/imports",
        data={"textbook_id": str(book["id"]), "adapter": "csv_template"},
        files={"file": ("template.csv", (FIXTURES / "template.csv").read_bytes(), "text/csv")},
    )
    assert response.status_code == 201, response.text
    job_id = response.json()["id"]
    rows = (await client.get(f"/api/v1/imports/{job_id}/rows")).json()["items"]
    for row in rows:
        if row["match_status"] == "ambiguous":
            await client.patch(
                f"/api/v1/imports/{job_id}/rows/{row['id']}",
                json={"chosen_word_id": row["candidate_word_ids"][0]},
            )
    response = await client.post(f"/api/v1/imports/{job_id}/commit?auto_furigana=false")
    assert response.status_code == 200, response.text
    entries = (await db.scalars(select(Entry))).all()
    assert entries and all(not e.auto_furigana and e.content_furigana is None for e in entries)


async def test_import_readings_include_later_rows(authorized, db):
    client, _ = authorized
    book = (await client.post("/api/v1/textbooks", json={"name": "Future headword"})).json()
    payload = {
        "rows": [
            {
                "kanji": "検証",
                "kana": "けんしょう",
                "lesson_no": 1,
                "order_no": 1,
                "content": [{"type": "example", "ja": "私は。"}],
            },
            {
                "kanji": "私",
                "kana": "わたくし",
                "lesson_no": 1,
                "order_no": 2,
                "content": [{"type": "meaning", "en": "I"}],
            },
        ]
    }
    result = await client.post(
        "/api/v1/imports",
        data={"textbook_id": str(book["id"]), "adapter": "normalized_json"},
        files={"file": ("rows.json", json.dumps(payload).encode(), "application/json")},
    )
    assert result.status_code == 201, result.text
    job_id = result.json()["id"]
    assert (await client.post(f"/api/v1/imports/{job_id}/commit")).json()["status"] == "done"
    first = await db.scalar(select(Entry).where(Entry.order_no == 1))
    assert first.content_furigana[0]["ja"] == "私[わたくし]は。"


async def test_furigana_save_api_original_and_backfill(imported, db):
    client, book, _ = imported
    user = await current_user(db, client.headers["authorization"][7:])
    lesson = await service.ensure_lesson(db, user, book["id"], 99)
    word = await dictionary.create_word(db, "腹痛", "ふくつう")
    source = [{"type": "example", "ja": "{{腹痛}}。私。"}]
    entry = await service.save_entry(db, user, lesson.id, word.id, 1, source)
    assert entry.content == source
    assert "腹痛[ふくつう]" in entry.content_furigana[0]["ja"]
    assert (await client.get(f"/api/v1/entries/{entry.id}?furigana=false")).json()["content"][0][
        "ja"
    ] == source[0]["ja"]
    assert (
        "私[わたし]" in (await client.get(f"/api/v1/entries/{entry.id}")).json()["content"][0]["ja"]
    )
    await service.save_entry(db, user, lesson.id, word.id, 1, source, auto_furigana=False)
    assert entry.content_furigana is None
    sessions = async_sessionmaker(
        bind=await db.connection(), expire_on_commit=False, join_transaction_mode="create_savepoint"
    )
    await db.execute(text("UPDATE textbook_entries SET content_furigana=NULL WHERE auto_furigana"))
    before = (
        await db.execute(select(Entry.id, Entry.content, Entry.search_text).order_by(Entry.id))
    ).all()
    dry = await backfill(sessions, dry_run=True, batch_size=1)
    assert dry["changed"] > 0
    assert (await backfill(sessions, batch_size=1))["changed"] == dry["changed"]
    assert (await backfill(sessions, batch_size=1))["changed"] == 0
    assert (
        await db.execute(select(Entry.id, Entry.content, Entry.search_text).order_by(Entry.id))
    ).all() == before
