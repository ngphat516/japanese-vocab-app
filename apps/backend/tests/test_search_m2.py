import pytest
from sqlalchemy import insert

from app.modules.auth.service import current_user
from app.modules.dictionary import service as dictionary
from app.modules.dictionary.models import WordSense
from app.modules.search.service import query_lemmas
from app.modules.textbooks import service as textbooks
from app.modules.textbooks.models import Entry, Lesson
from app.modules.textbooks.schemas import TextbookCreate
from tests.conftest import auth


@pytest.mark.parametrize(
    ("query", "target"), [("行かなかった", "行く"), ("食べました", "食べる"), ("緊張して", "緊張")]
)
async def test_SRCH_09_inflection(authorized, seeded, db, query, target):
    client, _ = authorized
    result = (await client.get("/api/v1/search", params={"q": query})).json()
    assert result["items"][0]["word"]["kanji"] == target
    assert result["items"][0]["matched_by"] == "lemma"


def test_SRCH_09_query_gate(monkeypatch):
    from app.modules.search import service

    def fail(_):
        raise AssertionError("Must not tokenize")

    monkeypatch.setattr(service, "lemmas", fail)
    for query in ["ikanakatta", "căng thẳng", "緊張 căng thẳng", "い", "いる", "ab"]:
        assert query_lemmas(query) == []


async def test_SRCH_09_rank_exact_lemma_prefix_meaning(authorized, db):
    client, _ = authorized
    base = await dictionary.create_word(db, "通う", "かよう")
    exact = await dictionary.create_word(db, "通い", "かよい")
    prefix = await dictionary.create_word(db, "通い道", "かよいみち")
    meaning = await dictionary.create_word(db, "別", "べつ")
    db.add(WordSense(word_id=meaning.id, lang="eng", gloss="通い", order=0))
    await db.flush()
    items = (await client.get("/api/v1/search", params={"q": "通い"})).json()["items"]
    assert [(i["word"]["id"], i["matched_by"]) for i in items][:4] == [
        (exact.id, "exact"),
        (base.id, "lemma"),
        (prefix.id, "prefix"),
        (meaning.id, "meaning"),
    ]
    assert "する" not in query_lemmas("緊張して")
    assert "為る" not in query_lemmas("緊張して")
    assert not query_lemmas("こと")
    assert (await client.get("/api/v1/search?q=ikanakatta")).json()["items"] == []


async def example_setup(client, db):
    user = await current_user(db, client.headers["authorization"][7:])
    book = await textbooks.create_textbook(db, user, TextbookCreate(name="Other textbook"))
    lesson = await textbooks.ensure_lesson(db, user, book.id, 1)
    target = await dictionary.create_word(db, "壁", "かべ")
    source = await dictionary.create_word(db, "穴", "あな")
    await textbooks.save_entry(
        db, user, lesson.id, target.id, 1, [{"type": "example", "ja": "壁に壁"}]
    )
    entry = await textbooks.save_entry(
        db,
        user,
        lesson.id,
        source.id,
        2,
        [
            {"type": "example", "ja": "{{かべ}}に穴をあける。", "vi": "Đục lỗ trên tường."},
            {"type": "example", "ja": "猫がいる。"},
            {
                "type": "usage",
                "context": "壁を作る",
                "variants": [
                    {"ja": "壁を直す", "correct": True},
                    {"ja": "穴を直す", "correct": False},
                ],
                "vi": "Dùng tường",
            },
            {"type": "collocation", "items": ["壁の色"]},
            {"type": "raw", "data": {"ocr_review_required": True}},
        ],
    )
    return user, book, lesson, target, source, entry


async def test_SRCH_10_visibility_sentence_filter_markup_ocr_and_pagination(authorized, db):
    client, _ = authorized
    _user, book, lesson, target, source, _entry = await example_setup(client, db)
    items = (await client.get("/api/v1/search", params={"q": "壁"})).json()["items"]
    assert items[0]["matched_by"] == "exact"
    assert items[0]["appears_in_examples"] == {"count": 1, "capped": False}
    endpoint = f"/api/v1/words/{target.id}/examples"
    result = (await client.get(endpoint, params={"size": 1})).json()
    assert result["total"] == 1
    first = result["items"][0]
    assert first["sentences"][0]["ja"] == "{{かべ}}に穴をあける。"
    assert first["sentences"][0]["vi"] == "Đục lỗ trên tường."
    assert first["textbook_id"] == book.id and first["lesson_id"] == lesson.id
    assert first["order_no"] == 2 and first["source_word"]["id"] == source.id
    assert first["ocr_review_required"] is True
    second = (await client.get(endpoint, params={"size": 1, "page": 2})).json()
    assert second["items"] == []
    assert [s["ja"] for s in first["sentences"]] == [
        "{{かべ}}に穴をあける。",
        "壁を作る",
        "壁を直す",
    ]
    assert (await client.get(endpoint, params={"size": 1, "page": 2})).json() == second
    assert (await client.get(endpoint, params={"page": 5})).json()["items"] == []
    assert (await client.get(endpoint, params={"page": 0})).status_code == 422
    assert (await client.get("/api/v1/words/999999/examples")).status_code == 404
    headers, _ = await auth(client, "other@example.com")
    client.headers.update(headers)
    assert (await client.get("/api/v1/search", params={"q": "壁"})).json()["items"][0][
        "appears_in_examples"
    ]["count"] == 0
    assert (await client.get(endpoint)).json()["items"] == []
    book.visibility = "public"
    await db.flush()
    assert (await client.get(endpoint)).json()["total"] == 1


async def test_SRCH_10_kana_only_formal_and_first_ten(authorized, db):
    client, _ = authorized
    _user, _book, _lesson, _target, _source, _entry = await example_setup(client, db)
    kana = await dictionary.create_word(db, "", "ネコ")
    assert (await client.get("/api/v1/search", params={"q": "ネコ"})).json()["items"][0][
        "appears_in_examples"
    ]["count"] == 1
    result = (await client.get(f"/api/v1/words/{kana.id}/examples")).json()
    assert [s["ja"] for i in result["items"] for s in i["sentences"]] == ["猫がいる。"]
    assert result["items"][0]["ocr_review_required"] is True
    formal = await dictionary.create_word(db, "", "こと")
    assert (await client.get("/api/v1/search?q=こと")).json()["items"][0][
        "appears_in_examples"
    ] is None
    assert (await client.get(f"/api/v1/words/{formal.id}/examples")).json()["total"] == 0
    for i in range(12):
        await dictionary.create_word(db, f"検証{i}", "けんしょう")
    items = (await client.get("/api/v1/search?q=検証&size=12")).json()["items"]
    assert all(i["appears_in_examples"] == {"count": 0, "capped": False} for i in items[:10])
    assert all(i["appears_in_examples"] is None for i in items[10:])
    assert (await client.get("/api/v1/search?q=検証&page=3&size=5")).json()["items"][0][
        "appears_in_examples"
    ] is None


async def test_SRCH_10_count_cap_and_gin_sql(authorized, db):
    client, _ = authorized
    user, book, _lesson, target, source, _entry = await example_setup(client, db)
    lessons = []
    for i in range(1000):
        row = Lesson(textbook_id=book.id, number=i + 2, title=f"Extra {i}")
        db.add(row)
        lessons.append(row)
    await db.flush()
    await db.execute(
        insert(Entry),
        [
            {
                "word_id": source.id,
                "lesson_id": row.id,
                "order_no": 1,
                "content": [{"type": "example", "ja": "壁"}],
                "search_text": "壁",
                "lemmas": ["壁"],
                "example_lemmas": ["壁"],
            }
            for row in lessons[:999]
        ],
    )
    desc = await dictionary.describe(db, target)
    assert (await textbooks.example_counts(db, user, [desc]))[target.id] == {
        "count": 1000,
        "capped": False,
    }
    await db.execute(
        insert(Entry),
        [
            {
                "word_id": source.id,
                "lesson_id": lessons[-1].id,
                "order_no": 1,
                "content": [{"type": "example", "ja": "壁"}],
                "search_text": "壁",
                "lemmas": ["壁"],
                "example_lemmas": ["壁"],
            }
        ],
    )
    assert (await textbooks.example_counts(db, user, [desc]))[target.id] == {
        "count": 1000,
        "capped": True,
    }
    examples = (await client.get(f"/api/v1/words/{target.id}/examples")).json()
    assert examples["total"] == 1000 and examples["total_capped"] is True
    assert len(examples["items"]) == 20
    sql = str(textbooks.example_entries(user, desc).limit(1001))
    assert "@>" in sql and "LIMIT" in sql


async def test_SRCH_09_lemma_filters_and_exact_label(imported):
    client, book, _ = imported
    result = (
        await client.get(
            "/api/v1/search", params={"q": "緊張して", "textbook_ids": book["id"], "jlpt": "N3"}
        )
    ).json()
    assert result["items"][0]["word"]["kanji"] == "緊張"
    assert result["items"][0]["matched_by"] == "lemma"
    assert (await client.get("/api/v1/search?q=緊張して&jlpt=N5")).json()["items"] == []
    assert (await client.get("/api/v1/search?q=緊張")).json()["items"][0]["matched_by"] == "exact"


async def test_SRCH_10_formal_count_null_but_examples_available(authorized, db):
    client, _ = authorized
    user, _book, lesson, _target, source, _entry = await example_setup(client, db)
    formal = await dictionary.create_word(db, "", "こと")
    await textbooks.save_entry(
        db, user, lesson.id, source.id, 2, [{"type": "example", "ja": "{{こと}}を決める。"}]
    )
    assert (await client.get("/api/v1/search?q=こと")).json()["items"][0][
        "appears_in_examples"
    ] is None
    items = (await client.get(f"/api/v1/words/{formal.id}/examples")).json()["items"]
    assert len(items) == 1 and items[0]["sentences"][0]["ja"] == "{{こと}}を決める。"
    assert items[0]["sentences"][0]["vi"] is None and items[0]["ocr_review_required"] is False


async def test_SRCH_09_meaning_sources_tie_by_id(authorized, db):
    client, _ = authorized
    user = await current_user(db, client.headers["authorization"][7:])
    book = await textbooks.create_textbook(db, user, TextbookCreate(name="Meaning tie"))
    lesson = await textbooks.ensure_lesson(db, user, book.id, 1)
    first = await dictionary.create_word(db, "先", "さき")
    second = await dictionary.create_word(db, "後", "あと")
    await textbooks.save_entry(
        db, user, lesson.id, first.id, 1, [{"type": "meaning", "en": "tiecheck"}]
    )
    db.add(WordSense(word_id=second.id, lang="eng", gloss="tiecheck", order=0))
    await db.flush()
    items = (await client.get("/api/v1/search?q=tiecheck")).json()["items"]
    assert [(i["word"]["id"], i["matched_by"]) for i in items] == [
        (first.id, "meaning"),
        (second.id, "meaning"),
    ]


async def test_m3_collocation_not_counted_and_entry_total_matches(authorized, db):
    client, _ = authorized
    user, _book, lesson, target, _source, _entry = await example_setup(client, db)
    other = await dictionary.create_word(db, "色", "いろ")
    await textbooks.save_entry(
        db, user, lesson.id, other.id, 3, [{"type": "collocation", "items": ["壁の色"]}]
    )
    result = (await client.get("/api/v1/search?q=壁")).json()["items"][0]
    examples = (await client.get(f"/api/v1/words/{target.id}/examples")).json()
    assert result["appears_in_examples"]["count"] == examples["total"] == 1
    assert len(examples["items"][0]["sentences"]) == 3
