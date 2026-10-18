from sqlalchemy import func, select

from app.modules.dictionary import service as dictionary
from app.modules.textbooks import service as s
from app.modules.textbooks.models import Entry
from tests.conftest import auth


async def test_TB_01_crud_and_private(authorized):
    client, _ = authorized
    created = await client.post(
        "/api/v1/textbooks",
        json={
            "name": "Private",
            "edition": "old",
            "license": "personal",
            "source_url": "https://example.com/book",
        },
    )
    assert created.status_code == 201
    book = created.json()
    assert (await client.get("/api/v1/textbooks")).json()["total"] == 1
    assert (
        await client.patch(f"/api/v1/textbooks/{book['id']}", json={"edition": "revised"})
    ).json()["edition"] == "revised"
    old_headers = dict(client.headers)
    headers, _ = await auth(client, "b@example.com")
    client.headers.update(headers)
    assert (await client.get("/api/v1/textbooks")).json()["items"] == []
    for method in ["get", "patch", "delete"]:
        kwargs = {"json": {"name": "hack"}} if method == "patch" else {}
        assert (
            await getattr(client, method)(f"/api/v1/textbooks/{book['id']}", **kwargs)
        ).status_code == 404
    client.headers.update(old_headers)
    assert (await client.delete(f"/api/v1/textbooks/{book['id']}")).status_code == 200


async def test_TB_02_lessons_crud(authorized):
    client, _ = authorized
    book = (await client.post("/api/v1/textbooks", json={"name": "Lessons"})).json()
    url = f"/api/v1/textbooks/{book['id']}/lessons"
    lesson = (await client.post(url, json={"number": 1, "title": "Unit 1"})).json()
    assert len((await client.get(url)).json()) == 1
    assert (await client.post(url, json={"number": 1, "title": "Duplicate"})).status_code == 409
    assert (
        await client.patch(f"/api/v1/lessons/{lesson['id']}", json={"title": "Updated"})
    ).json()["title"] == "Updated"
    assert (await client.delete(f"/api/v1/lessons/{lesson['id']}")).status_code == 200
    assert (await client.delete(f"/api/v1/lessons/{lesson['id']}")).status_code == 404


async def test_TB_03_entries_order_pagination(imported):
    client, book, _ = imported
    lessons = (await client.get(f"/api/v1/textbooks/{book['id']}/lessons")).json()
    lesson = next(x for x in lessons if x["number"] == 5)
    result = (await client.get(f"/api/v1/lessons/{lesson['id']}/entries?size=1")).json()
    assert result["total"] == 2
    assert len(result["items"]) == 1
    assert result["items"][0]["order_no"] == 357
    assert (await client.get(f"/api/v1/entries/{result['items'][0]['id']}")).status_code == 200


async def test_TB_04_full_blocks(imported):
    client, _, _ = imported
    entry = (await client.get("/api/v1/search?q=きんちょう")).json()["items"][0]["entries"][0]
    assert [b["type"] for b in entry["content"]] == [
        "meaning",
        "example",
        "usage",
        "collocation",
        "synonym",
        "antonym",
        "raw",
    ]


async def test_TB_05_regenerate_search_text(imported, db):
    client, _, _ = imported
    from app.modules.auth.service import current_user

    user = await current_user(db, client.headers["authorization"][7:])
    entry = await db.scalar(select(Entry).order_by(Entry.id))
    assert "{{" not in entry.search_text and "[" not in entry.search_text
    await s.save_entry(
        db,
        user,
        entry.lesson_id,
        entry.word_id,
        entry.order_no,
        [{"type": "example", "ja": "{{更新[こうしん]する}}", "vi": "mới"}],
    )
    assert entry.search_text == "更新する mới"


async def test_textbook_delete_cascade_preserves_words(imported, db):
    client, book, _ = imported
    word = (await dictionary.match(db, "緊張", "きんちょう"))[0]
    assert (await client.delete(f"/api/v1/textbooks/{book['id']}")).status_code == 200
    assert await db.scalar(select(func.count()).select_from(Entry)) == 0
    assert await dictionary.get_word(db, word.id)
