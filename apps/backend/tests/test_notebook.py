from datetime import UTC, datetime

import pytest
from sqlalchemy import event, func, insert, select

from app.modules.auth.service import current_user
from app.modules.dictionary import service as dictionary
from app.modules.dictionary.models import Word
from app.modules.notebook.models import CollectionWord, SearchHistory
from app.modules.textbooks import service as textbooks
from tests.conftest import auth


async def target(client):
    return (await client.get("/api/v1/search?q=緊張して")).json()["items"][0]["word"]["id"]


async def test_m3_history_saved_collection_flow(imported, db):
    client, book, _ = imported
    word_id = await target(client)
    assert (await client.get("/api/v1/history")).json()["total"] == 0
    first = await client.get(f"/api/v1/words/{word_id}")
    assert first.status_code == 200 and first.json()["word"]["saved"] is False
    history = (await client.get("/api/v1/history")).json()
    assert history["total"] == 1
    old_time = history["items"][0]["searched_at"]
    await client.get(f"/api/v1/words/{word_id}")
    history = (await client.get("/api/v1/history")).json()
    assert history["total"] == 1 and history["items"][0]["searched_at"] >= old_time
    saved = (
        await client.post(
            "/api/v1/saved-words",
            json={
                "word_id": word_id,
                "note": "Remember this",
                "tags": [" Ａ ", "A", "tag", "", " tag "],
            },
        )
    ).json()
    assert saved["word"]["saved"] is True and saved["tags"] == ["A", "tag"]
    assert saved["sources"][0]["textbook_id"] == book["id"]
    duplicate = (await client.post("/api/v1/saved-words", json={"word_id": word_id})).json()
    assert duplicate["id"] == saved["id"] and duplicate["note"] == "Remember this"
    collection = (await client.post("/api/v1/collections", json={"name": " Ｎ３ "})).json()
    assert collection["name"] == "N3"
    endpoint = f"/api/v1/collections/{collection['id']}/words"
    assert (await client.post(endpoint, json={"saved_word_ids": [saved["id"]]})).json()[
        "word_count"
    ] == 1
    assert (await client.post(endpoint, json={"saved_word_ids": [saved["id"]]})).json()[
        "word_count"
    ] == 1
    assert (await client.get("/api/v1/collections")).json()["items"][0]["word_count"] == 1
    assert (
        await client.get("/api/v1/saved-words", params={"collection_id": collection["id"]})
    ).json()["total"] == 1
    assert (
        await client.patch(f"/api/v1/collections/{collection['id']}", json={"name": "My N3"})
    ).json()["name"] == "My N3"
    assert (await client.get("/api/v1/search?q=緊張")).json()["items"][0]["word"]["saved"] is True
    assert (await client.get(f"/api/v1/words/{word_id}")).json()["word"]["saved"] is True
    patch = await client.patch(
        f"/api/v1/saved-words/{saved['id']}", json={"note": "Updated", "tags": ["review"]}
    )
    assert patch.json()["tags"] == ["review"]
    assert (
        await client.request("DELETE", endpoint, json={"saved_word_ids": [saved["id"]]})
    ).json()["word_count"] == 0
    await client.post(endpoint, json={"saved_word_ids": [saved["id"]]})
    assert (await client.delete(f"/api/v1/saved-words/{saved['id']}")).status_code == 200
    assert await db.scalar(select(func.count()).select_from(CollectionWord)) == 0
    assert (await client.get("/api/v1/search?q=緊張")).json()["items"][0]["word"]["saved"] is False
    assert (await client.delete(f"/api/v1/collections/{collection['id']}")).status_code == 200
    assert (await client.delete("/api/v1/history")).status_code == 200
    assert (await client.get("/api/v1/history")).json()["total"] == 0


async def test_m3_filters_stats_pagination_and_one_saved_query(imported, db):
    client, book, _ = imported
    word_id = await target(client)
    await client.post("/api/v1/saved-words", json={"word_id": word_id, "tags": ["review"]})
    word = await dictionary.create_word(db, "外", "そと", jmdict_id="synthetic-test-only")
    await client.post("/api/v1/saved-words", json={"word_id": word.id})
    assert (await client.get("/api/v1/saved-words/stats")).json() == {
        "N1": 0,
        "N2": 0,
        "N3": 1,
        "N4": 0,
        "N5": 0,
        "none": 1,
    }
    for filters in [
        {"jlpt": "N3"},
        {"jlpt": "none"},
        {"tag": "review"},
        {"textbook_id": book["id"]},
    ]:
        assert (await client.get("/api/v1/saved-words", params=filters)).json()["total"] == 1
    assert (await client.get("/api/v1/saved-words?size=1&page=2")).json()["total"] == 2
    assert len((await client.get("/api/v1/saved-words?size=1&page=2")).json()["items"]) == 1
    assert (await client.get("/api/v1/saved-words?jlpt=N9")).status_code == 422
    statements = []

    def capture(conn, cursor, statement, parameters, context, executemany):
        if "FROM saved_words" in statement:
            statements.append(statement)

    event.listen(db.sync_session.bind, "before_cursor_execute", capture)
    try:
        assert (await client.get("/api/v1/search?q=緊")).status_code == 200
    finally:
        event.remove(db.sync_session.bind, "before_cursor_execute", capture)
    assert len(statements) == 1


async def test_m3_history_limit_upsert_and_user_isolation(authorized, seeded, db):
    client, _ = authorized
    user = await current_user(db, client.headers["authorization"][7:])
    await db.execute(
        insert(Word),
        [
            {
                "kanji": f"履歴{i}",
                "kana": f"りれき{i}",
                "kana_norm": f"りれき{i}",
                "romaji": str(i),
                "jmdict_id": str(i),
            }
            for i in range(501)
        ],
    )
    ids = list(
        (
            await db.scalars(select(Word.id).where(Word.kanji.startswith("履歴")).order_by(Word.id))
        ).all()
    )
    await db.execute(
        insert(SearchHistory),
        [
            {
                "user_id": user.id,
                "word_id": word_id,
                "query": str(word_id),
                "searched_at": datetime(2020, 1, 1, tzinfo=UTC),
            }
            for word_id in ids[:500]
        ],
    )
    assert (await client.get(f"/api/v1/words/{ids[-1]}")).status_code == 200
    assert (
        await db.scalar(
            select(func.count()).select_from(SearchHistory).where(SearchHistory.user_id == user.id)
        )
        == 500
    )
    assert (
        await db.scalar(
            select(SearchHistory.id).where(
                SearchHistory.user_id == user.id, SearchHistory.word_id == ids[0]
            )
        )
        is None
    )
    await client.get(f"/api/v1/words/{ids[1]}")
    assert (await client.get("/api/v1/history?size=1")).json()["items"][0]["word"]["id"] == ids[1]
    old_headers = dict(client.headers)
    headers, _ = await auth(client, "history-b@example.com")
    client.headers.update(headers)
    assert (await client.get("/api/v1/history")).json()["total"] == 0
    await client.get(f"/api/v1/words/{ids[-1]}")
    await client.delete("/api/v1/history")
    client.headers.update(old_headers)
    assert (await client.get("/api/v1/history")).json()["total"] == 500


async def test_m3_ownership_visibility_and_revocation(imported, db):
    client, book, _ = imported
    user = await current_user(db, client.headers["authorization"][7:])
    lesson = await textbooks.ensure_lesson(db, user, book["id"], 99)
    private = await dictionary.create_word(db, "限定", "げんてい")
    await textbooks.save_entry(
        db, user, lesson.id, private.id, 1, [{"type": "meaning", "vi": "Riêng"}]
    )
    saved = (await client.post("/api/v1/saved-words", json={"word_id": private.id})).json()
    collection = (await client.post("/api/v1/collections", json={"name": "Private"})).json()
    own_headers = dict(client.headers)
    headers, _ = await auth(client, "notebook-b@example.com")
    client.headers.update(headers)
    assert (
        await client.post("/api/v1/saved-words", json={"word_id": private.id})
    ).status_code == 404
    assert (await client.get(f"/api/v1/words/{private.id}")).status_code == 404
    assert (
        await client.patch(f"/api/v1/saved-words/{saved['id']}", json={"note": "x"})
    ).status_code == 404
    assert (await client.delete(f"/api/v1/saved-words/{saved['id']}")).status_code == 404
    for method, path, payload in [
        ("PATCH", f"/api/v1/collections/{collection['id']}", {"name": "x"}),
        ("DELETE", f"/api/v1/collections/{collection['id']}", None),
        (
            "POST",
            f"/api/v1/collections/{collection['id']}/words",
            {"saved_word_ids": [saved["id"]]},
        ),
    ]:
        assert (await client.request(method, path, json=payload)).status_code == 404
    own_collection = (await client.post("/api/v1/collections", json={"name": "B"})).json()
    assert (
        await client.post(
            f"/api/v1/collections/{own_collection['id']}/words",
            json={"saved_word_ids": [saved["id"]]},
        )
    ).status_code == 404
    assert (
        await client.get("/api/v1/saved-words", params={"collection_id": collection["id"]})
    ).status_code == 404
    assert (await client.get("/api/v1/saved-words")).json()["total"] == 0
    # A public textbook grants access; removing that access hides saved rows/sources again.
    book_row = await db.get(
        __import__("app.modules.textbooks.models", fromlist=["Textbook"]).Textbook, book["id"]
    )
    book_row.visibility = "public"
    await db.flush()
    assert (
        await client.post("/api/v1/saved-words", json={"word_id": private.id})
    ).status_code == 201
    book_row.visibility = "private"
    await db.flush()
    assert (await client.get("/api/v1/saved-words")).json()["total"] == 0
    client.headers.update(own_headers)
    assert (await client.get("/api/v1/saved-words")).json()["total"] == 1


@pytest.mark.parametrize(
    "payload",
    [{"tags": ["x" * 31]}, {"tags": [str(i) for i in range(21)]}, {"tags": None}, {"note": None}],
)
async def test_m3_tag_and_note_validation(authorized, seeded, payload):
    client, _ = authorized
    saved = (
        await client.post("/api/v1/saved-words", json={"word_id": await target(client)})
    ).json()
    assert (
        await client.patch(f"/api/v1/saved-words/{saved['id']}", json=payload)
    ).status_code == 422


async def test_m3_collection_conflicts_and_empty_stats(authorized):
    client, _ = authorized
    assert set((await client.get("/api/v1/saved-words/stats")).json().values()) == {0}
    one = (await client.post("/api/v1/collections", json={"name": "One"})).json()
    two = (await client.post("/api/v1/collections", json={"name": "Two"})).json()
    assert (await client.post("/api/v1/collections", json={"name": " One "})).status_code == 409
    assert (
        await client.patch(f"/api/v1/collections/{two['id']}", json={"name": "One"})
    ).status_code == 409
    assert (await client.post("/api/v1/collections", json={"name": " "})).status_code == 422
    assert (
        await client.post(
            f"/api/v1/collections/{one['id']}/words", json={"saved_word_ids": [999999]}
        )
    ).status_code == 404


@pytest.mark.parametrize(
    ("method", "path", "payload"),
    [
        ("GET", "/history", None),
        ("DELETE", "/history", None),
        ("GET", "/saved-words", None),
        ("POST", "/saved-words", {"word_id": 1}),
        ("PATCH", "/saved-words/1", {"note": "x"}),
        ("DELETE", "/saved-words/1", None),
        ("GET", "/saved-words/stats", None),
        ("GET", "/collections", None),
        ("POST", "/collections", {"name": "x"}),
        ("PATCH", "/collections/1", {"name": "x"}),
        ("DELETE", "/collections/1", None),
        ("POST", "/collections/1/words", {"saved_word_ids": [1]}),
        ("DELETE", "/collections/1/words", {"saved_word_ids": [1]}),
    ],
)
async def test_m3_notebook_requires_auth(client, method, path, payload):
    assert (await client.request(method, "/api/v1" + path, json=payload)).status_code == 401


async def test_m3_migration_upgrade_downgrade_upgrade(pg_url):
    import asyncio
    import os
    import subprocess

    from sqlalchemy import text
    from sqlalchemy.ext.asyncio import create_async_engine

    engine = create_async_engine(pg_url)
    try:
        for direction, version in [("downgrade", "0003_entry_lemmas"), ("upgrade", "head")]:
            await asyncio.to_thread(
                subprocess.run,
                [os.sys.executable, "-m", "alembic", direction, version],
                env={**os.environ, "DATABASE_URL": pg_url},
                check=True,
                capture_output=True,
            )
            async with engine.connect() as conn:
                tables = set(
                    (
                        await conn.execute(
                            text("SELECT tablename FROM pg_tables WHERE schemaname='public'")
                        )
                    ).scalars()
                )
                if direction == "downgrade":
                    assert (
                        not {"search_history", "saved_words", "collections", "collection_words"}
                        & tables
                    )
                    assert (
                        await conn.scalar(
                            text(
                                "SELECT count(*) FROM information_schema.columns WHERE table_name='textbook_entries' AND column_name='example_lemmas'"
                            )
                        )
                        == 0
                    )
                else:
                    assert {
                        "search_history",
                        "saved_words",
                        "collections",
                        "collection_words",
                    } <= tables
                    indexes = set(
                        (
                            await conn.execute(
                                text("SELECT indexname FROM pg_indexes WHERE schemaname='public'")
                            )
                        ).scalars()
                    )
                    assert {
                        "ix_entries_example_lemmas",
                        "ix_history_user_searched",
                        "ix_saved_user_created",
                        "uq_saved_user_word",
                        "uq_collection_user_name",
                    } <= indexes
    finally:
        await engine.dispose()
