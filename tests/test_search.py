import pytest

from app.modules.dictionary import service as dictionary
from tests.conftest import auth


@pytest.mark.parametrize("query", ["きんちょう", "キン チョウ", "kinchou", "緊張", "căng thẳng"])
async def test_SRCH_01_normalization_full_flow(imported, query):
    client, _, _ = imported
    response = await client.get("/api/v1/search", params={"q": query})
    assert response.status_code == 200, response.text
    item = response.json()["items"][0]
    assert item["word"]["kanji"] == "緊張"
    assert item["word"]["hanviet"] == "KHẨN TRƯƠNG"
    assert item["word"]["jlpt_level"] == "N3"
    assert item["word"]["kanji_breakdown"] == [
        {"char": "緊", "hanviet": "KHẨN"},
        {"char": "張", "hanviet": "TRƯƠNG"},
    ]
    assert len(item["entries"][0]["content"]) == 7


async def test_SRCH_02_detect_query(imported):
    client, _, _ = imported
    for query in ["緊", "きん", "căng thẳng"]:
        assert (await client.get("/api/v1/search", params={"q": query})).json()["items"][0]["word"][
            "kanji"
        ] == "緊張"


async def test_SRCH_03_prefix_trigram(imported):
    client, _, _ = imported
    assert (await client.get("/api/v1/search?q=緊")).json()["total"] == 1
    assert (await client.get("/api/v1/search?q=tension")).json()["items"][0]["word"][
        "kanji"
    ] == "緊張"


async def test_SRCH_04_returns_full_blocks(imported):
    client, _, _ = imported
    item = (await client.get("/api/v1/search?q=きんちょう")).json()["items"][0]
    assert {"word", "entries"} <= item.keys()
    assert {"hanviet", "kanji_breakdown", "jlpt_level"} <= item["word"].keys()
    blocks = item["entries"][0]["content"]
    assert next(b for b in blocks if b["type"] == "usage")["variants"][1]["correct"] is False


async def test_SRCH_05_private_visibility(imported):
    client, book, _ = imported
    headers, _ = await auth(client, "b@example.com")
    client.headers.update(headers)
    items = (await client.get("/api/v1/search?q=緊張")).json()["items"]
    assert items[0]["entries"] == []
    assert (await client.get("/api/v1/search?q=căng thẳng")).json()["items"] == []
    assert (
        await client.get("/api/v1/search", params={"q": "緊張", "textbook_ids": book["id"]})
    ).json()["items"] == []
    assert (await client.get("/api/v1/words/" + str(items[0]["word"]["id"]))).json()[
        "entries"
    ] == []


async def test_SRCH_06_filters_rank(imported, db):
    client, book, _ = imported
    await dictionary.create_word(db, "緊張感", "きんちょうかん")
    result = (await client.get("/api/v1/search?q=緊張")).json()
    assert [x["word"]["kanji"] for x in result["items"]][:2] == ["緊張", "緊張感"]
    assert (
        await client.get(
            "/api/v1/search", params={"q": "緊張", "textbook_ids": book["id"], "jlpt": "N3"}
        )
    ).json()["total"] == 1
    assert (await client.get("/api/v1/search?q=緊張&jlpt=N5")).json()["items"] == []


async def test_SRCH_07_first_ten_full_later_summary(authorized, seeded, db):
    client, _ = authorized
    from app.modules.auth.service import current_user
    from app.modules.textbooks import service as textbooks
    from app.modules.textbooks.schemas import TextbookCreate

    user = await current_user(db, client.headers["authorization"][7:])
    book = await textbooks.create_textbook(db, user, TextbookCreate(name="pagination"))
    lesson = await textbooks.ensure_lesson(db, user, book.id, 1)
    for i in range(12):
        word = await dictionary.create_word(db, f"試験{i}", f"しけん{i}")
        await textbooks.save_entry(
            db, user, lesson.id, word.id, i + 1, [{"type": "meaning", "vi": "test"}]
        )
    result = (await client.get("/api/v1/search?q=試験&size=12")).json()
    assert result["total"] == 12
    assert all(x["entries"][0]["content"] for x in result["items"][:10])
    assert all(x["entries"][0]["content"] is None for x in result["items"][10:])
    word_id = result["items"][11]["word"]["id"]
    assert (await client.get(f"/api/v1/words/{word_id}")).json()["entries"][0]["content"]
    second_page = (await client.get("/api/v1/search?q=試験&size=5&page=3")).json()
    assert len(second_page["items"]) == 2
    assert second_page["items"][0]["entries"][0]["content"] is None


async def test_search_invalid_query_and_health(authorized):
    client, _ = authorized
    assert (await client.get("/health")).json()["database"] == "ok"
    response = await client.get("/api/v1/search?q=%20%20")
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "EMPTY_QUERY"
    assert "x-request-id" in response.headers
