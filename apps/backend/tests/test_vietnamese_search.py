from sqlalchemy import select

from app.modules.dictionary import service as dictionary
from app.modules.dictionary.models import WordSense
from app.modules.textbooks.models import Entry, Lesson


async def test_vietnamese_only_searches_vi_meanings_and_vie_senses(imported, db):
    client, book, _ = imported
    lesson = await db.scalar(select(Lesson).where(Lesson.textbook_id == book["id"]))
    ids = {}
    for kind in ["eng", "vie", "example", "meaning_en"]:
        word = await dictionary.create_word(db, kind, "ご")
        ids[kind] = word.id
        if kind in {"eng", "vie"}:
            db.add(WordSense(word_id=word.id, lang=kind, gloss="căng thẳng", order=0))
        else:
            content = (
                [{"type": "example", "ja": "試験", "vi": "căng thẳng"}]
                if kind == "example"
                else [{"type": "meaning", "en": "căng thẳng"}]
            )
            db.add(
                Entry(
                    word_id=word.id,
                    lesson_id=lesson.id,
                    order_no=100,
                    content=content,
                    search_text="căng thẳng",
                )
            )
    await db.flush()
    result = (await client.get("/api/v1/search", params={"q": "căng thẳng"})).json()
    found = {item["word"]["id"] for item in result["items"]}
    assert ids["vie"] in found
    assert not found.intersection({ids["eng"], ids["example"], ids["meaning_en"]})
    assert any(
        any(e["textbook_id"] == book["id"] for e in item["entries"]) for item in result["items"]
    )
