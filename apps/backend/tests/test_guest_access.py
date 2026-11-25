"""Guests (no token) may read public data: search, word detail, examples, kanji."""

from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.core import rate_limit
from app.core.config import get_settings
from app.modules.auth.service import current_user
from app.modules.dictionary import service as dictionary
from app.modules.notebook.models import SearchHistory
from app.modules.textbooks import service as textbooks
from app.modules.textbooks.models import Textbook
from app.modules.textbooks.schemas import TextbookCreate


def as_guest(client):
    client.headers.pop("authorization", None)
    return client


async def make_public(db, book_id):
    (await db.get(Textbook, book_id)).visibility = "public"
    await db.flush()


async def history_rows(db):
    return await db.scalar(select(func.count()).select_from(SearchHistory))


async def test_guest_search_returns_public_results(imported, db):
    client, book, _ = imported
    await make_public(db, book["id"])
    as_guest(client)
    response = await client.get("/api/v1/search", params={"q": "緊張"})
    assert response.status_code == 200, response.text
    item = response.json()["items"][0]
    assert item["word"]["kanji"] == "緊張"
    assert item["word"]["saved"] is False
    assert [e["textbook_id"] for e in item["entries"]] == [book["id"]]
    assert item["entries"][0]["content"]


async def test_guest_cannot_see_private_textbook(imported, db):
    client, book, _ = imported  # owner A; the imported book stays private
    owner = await current_user(db, client.headers["authorization"][7:])
    secret_book = await textbooks.create_textbook(db, owner, TextbookCreate(name="Secret"))
    lesson = await textbooks.ensure_lesson(db, owner, secret_book.id, 1)
    secret = await dictionary.create_word(db, "秘語", "ひご")
    await textbooks.save_entry(
        db, owner, lesson.id, secret.id, 1, [{"type": "meaning", "vi": "từ bí mật"}]
    )
    # Sanity: the owner sees both.
    assert (await client.get(f"/api/v1/words/{secret.id}")).status_code == 200
    owner_items = (await client.get("/api/v1/search", params={"q": "緊張"})).json()["items"]
    assert owner_items[0]["entries"]

    as_guest(client)
    items = (await client.get("/api/v1/search", params={"q": "緊張"})).json()["items"]
    assert items[0]["word"]["kanji"] == "緊張"  # JMdict word is public
    assert items[0]["entries"] == []  # but the private textbook entry is not
    assert (
        await client.get("/api/v1/search", params={"q": "緊張", "textbook_ids": book["id"]})
    ).json()["items"] == []
    assert (await client.get("/api/v1/search", params={"q": "từ bí mật"})).json()["items"] == []
    found = (await client.get("/api/v1/search", params={"q": "秘語"})).json()["items"]
    # Headword matching does not filter by readability (pre-existing, same for any logged-in
    # user), but the private entry itself must never be returned.
    assert all(i["entries"] == [] for i in found if i["word"]["id"] == secret.id)

    detail = await client.get(f"/api/v1/words/{items[0]['word']['id']}")
    assert detail.status_code == 200 and detail.json()["entries"] == []
    missing = await client.get(f"/api/v1/words/{secret.id}")
    assert missing.status_code == 404
    assert missing.json()["error"]["code"] == "WORD_NOT_FOUND"


async def test_guest_word_detail_no_history(imported, db):
    client, book, _ = imported
    await make_public(db, book["id"])
    word_id = (await client.get("/api/v1/search", params={"q": "緊張"})).json()["items"][0]["word"][
        "id"
    ]
    await client.post("/api/v1/saved-words", json={"word_id": word_id})  # saved by A
    before = await history_rows(db)

    as_guest(client)
    response = await client.get(f"/api/v1/words/{word_id}")
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["word"]["saved"] is False
    assert body["entries"]
    assert await history_rows(db) == before


async def test_guest_examples_and_kanji(imported, db):
    client, book, _ = imported
    await make_public(db, book["id"])
    as_guest(client)
    word_id = (await client.get("/api/v1/search", params={"q": "緊張"})).json()["items"][0]["word"][
        "id"
    ]
    examples = await client.get(f"/api/v1/words/{word_id}/examples")
    assert examples.status_code == 200, examples.text
    assert {"items", "total", "page", "size"} <= examples.json().keys()
    kanji = await client.get("/api/v1/kanji/緊")
    assert kanji.status_code == 200, kanji.text
    assert kanji.json()["char"] == "緊"
    assert "緊張" in [w["kanji"] for w in kanji.json()["words"]["items"]]


async def test_invalid_token_still_401(client, seeded):
    headers = {"Authorization": "Bearer not-a-real-token"}
    for path in ["/search?q=緊張", "/words/1", "/words/1/examples", "/kanji/緊"]:
        response = await client.get("/api/v1" + path, headers=headers)
        assert response.status_code == 401, (path, response.text)


async def test_write_routes_still_require_auth(client, seeded):
    assert (await client.post("/api/v1/saved-words", json={"word_id": 1})).status_code == 401
    assert (await client.get("/api/v1/history")).status_code == 401
    assert (await client.get("/api/v1/saved-words")).status_code == 401
    assert (await client.patch("/api/v1/words/1", json={"hanviet": "X"})).status_code == 401
    assert (await client.patch("/api/v1/kanji/緊", json={"hanviet": ["X"]})).status_code == 401
    assert (await client.get("/api/v1/me")).status_code == 401


async def test_guest_search_rate_limited_by_ip(client, seeded, db, monkeypatch):
    monkeypatch.setattr(get_settings(), "rate_limit_enabled", True)
    monkeypatch.setattr(
        rate_limit,
        "Session",
        async_sessionmaker(
            bind=db.bind, expire_on_commit=False, join_transaction_mode="create_savepoint"
        ),
    )

    class FixedTime:
        @staticmethod
        def now(tz):
            return datetime(2026, 11, 25, 0, 0, tzinfo=UTC)

    monkeypatch.setattr(rate_limit, "datetime", FixedTime)
    for _ in range(60):
        assert (await client.get("/api/v1/search?q=緊張")).status_code == 200
    response = await client.get("/api/v1/search?q=緊張")
    assert response.status_code == 429
    assert response.json()["error"]["code"] == "RATE_LIMITED"
    key = (await db.execute(select(rate_limit.RateBucket.key))).scalars().all()
    assert key == ["search:127.0.0.1"]
