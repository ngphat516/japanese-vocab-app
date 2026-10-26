from sqlalchemy import text


async def test_NFR_01_large_prefix_paginates_before_loading(authorized, db):
    """The old implementation passes all 40k ids to asyncpg and exceeds its limit."""
    client, _ = authorized
    await db.execute(
        text("""
        INSERT INTO words(kanji,kana,kana_norm,romaji,hanviet,pos)
        SELECT '規模' || n,'い' || n,'い' || n,'i' || n,'','{}'
        FROM generate_series(1,40000) n
    """)
    )
    response = await client.get("/api/v1/search", params={"q": "い", "size": 20, "page": 2})
    assert response.status_code == 200, response.text
    result = response.json()
    assert result["total"] == 1000
    assert result["total_capped"] is True
    assert len(result["items"]) == 20
    assert [item["word"]["kanji"] for item in result["items"]] == [
        f"規模{n}" for n in range(21, 41)
    ]


async def test_kana_prefix_does_not_match_inside_reading(authorized, db):
    from app.modules.dictionary import service

    client, _ = authorized
    expected = await service.create_word(db, "犬", "いぬ")
    await service.create_word(db, "貝", "かい")
    await service.create_word(db, "緊張", "きんちょう")
    result = (await client.get("/api/v1/search", params={"q": "い"})).json()
    assert result["total"] == 1
    assert result["total_capped"] is False
    assert [item["word"]["id"] for item in result["items"]] == [expected.id]


async def test_short_latin_meaning_prefix_in_senses_and_entries(authorized, db):
    from sqlalchemy import select

    from app.modules.dictionary import service
    from app.modules.dictionary.models import WordSense
    from app.modules.textbooks.models import Entry, Lesson

    client, _ = authorized
    book = (await client.post("/api/v1/textbooks", json={"name": "Prefix test"})).json()
    await client.post(
        f"/api/v1/textbooks/{book['id']}/lessons", json={"number": 1, "title": "Test"}
    )
    expected = []
    for n, gloss in enumerate(["Apple", "ABacus", "cab", "table", "a_b", "a%b"]):
        word = await service.create_word(db, f"語{n}", f"ご{n}")
        db.add(WordSense(word_id=word.id, gloss=gloss, lang="en", order=0))
        if n < 2 or n > 3:
            expected.append(word.id)
    lesson = await db.scalar(select(Lesson).where(Lesson.textbook_id == book["id"]))
    entry_word = await service.create_word(db, "記録", "きろく")
    db.add(
        Entry(
            word_id=entry_word.id,
            lesson_id=lesson.id,
            order_no=99,
            content=[{"type": "meaning", "en": "ABout"}],
            search_text="ABout",
        )
    )
    await db.flush()
    result = (await client.get("/api/v1/search", params={"q": "a"})).json()
    assert {item["word"]["id"] for item in result["items"]} == {*expected, entry_word.id}
    result = (await client.get("/api/v1/search", params={"q": "ab"})).json()
    assert {item["word"]["id"] for item in result["items"]} == {expected[1], entry_word.id}


async def test_total_cap_boundary_deduplicates_senses(authorized, db):
    from sqlalchemy import event

    client, _ = authorized
    await db.execute(
        text("""
        INSERT INTO words(kanji,kana,kana_norm,romaji,hanviet,pos)
        SELECT '境界' || n,'う' || n,'う' || n,'u' || n,'','{}'
        FROM generate_series(1,1000) n
    """)
    )
    await db.execute(
        text("""
        INSERT INTO word_senses(word_id,lang,gloss,"order")
        SELECT id,'en','Umbrella',0 FROM words
        UNION ALL SELECT id,'en','Umbrellas',1 FROM words
    """)
    )
    statements = []

    def capture(conn, cursor, statement, parameters, context, executemany):
        if "count(*)" in statement.lower():
            statements.append((statement, parameters))

    event.listen(db.sync_session.bind, "before_cursor_execute", capture)
    try:
        exact = (await client.get("/api/v1/search", params={"q": "um"})).json()
    finally:
        event.remove(db.sync_session.bind, "before_cursor_execute", capture)
    assert len(statements) == 1
    statement, parameters = statements[0]
    assert "LIMIT" in statement
    assert 1001 in parameters
    assert "FROM (SELECT DISTINCT" in statement
    assert exact["total"] == 1000
    assert exact["total_capped"] is False
    await db.execute(
        text("""
        INSERT INTO words(kanji,kana,kana_norm,romaji,hanviet,pos)
        VALUES ('境界追加','う','う','u','','{}')
    """)
    )
    result = (await client.get("/api/v1/search", params={"q": "う"})).json()
    assert result["total"] == 1000
    assert result["total_capped"] is True
