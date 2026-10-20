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
    assert result["total"] == 40000
    assert len(result["items"]) == 20
    assert [item["word"]["kanji"] for item in result["items"]] == [
        f"規模{n}" for n in range(21, 41)
    ]
