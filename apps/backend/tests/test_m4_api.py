from sqlalchemy import func, select

from app.modules.auth.service import current_user
from app.modules.dictionary import service as dictionary
from app.modules.dictionary.models import Kanji, WordEdit
from app.modules.textbooks import service as textbooks
from app.modules.textbooks.schemas import TextbookCreate
from tests.conftest import auth


async def test_admin_word_patch_audit_and_kanji_visibility(authorized, seeded, db):
    client, _ = authorized
    user = await current_user(db, client.headers["authorization"][7:])
    word = await dictionary.create_word(db, "検証", "けんしょう", jmdict_id="test")
    private = await dictionary.create_word(db, "検査", "けんさ")
    db.add(Kanji(char="検", meaning="examine", strokes=12, hanviet=["KIỂM"], jlpt_level="N2"))
    book = await textbooks.create_textbook(db, user, TextbookCreate(name="Hidden"))
    lesson = await textbooks.ensure_lesson(db, user, book.id, 1)
    await textbooks.save_entry(
        db, user, lesson.id, private.id, 1, [{"type": "meaning", "en": "check"}]
    )
    assert (
        await client.patch(f"/api/v1/words/{word.id}", json={"hanviet": "KIỂM CHỨNG"})
    ).status_code == 403
    user.role = "admin"
    await db.flush()
    response = await client.patch(f"/api/v1/words/{word.id}", json={"hanviet": "KIỂM CHỨNG"})
    assert response.status_code == 200 and response.json()["hanviet"] == "KIỂM CHỨNG"
    edit = await db.scalar(select(WordEdit).where(WordEdit.word_id == word.id))
    assert (edit.old, edit.new, edit.user_id, edit.field) == (
        "",
        "KIỂM CHỨNG",
        user.id,
        "hanviet",
    )
    await client.patch(f"/api/v1/words/{word.id}", json={"hanviet": "KIỂM CHỨNG"})
    assert await db.scalar(select(func.count()).select_from(WordEdit)) == 1
    assert (await client.patch("/api/v1/words/999999", json={"hanviet": ""})).status_code == 404
    assert (
        await client.patch(f"/api/v1/words/{word.id}", json={"hanviet": None})
    ).status_code == 422
    assert (await client.get("/api/v1/kanji/あ")).status_code == 422
    assert (await client.get("/api/v1/kanji/検証")).status_code == 422
    assert (await client.get("/api/v1/kanji/龘")).status_code == 404
    own = (await client.get("/api/v1/kanji/検?size=1&page=2")).json()
    assert own["words"]["total"] == 2 and own["words"]["items"][0]["id"] == private.id
    headers, _ = await auth(client, "kanji-other@example.com")
    client.headers.update(headers)
    other = (await client.get("/api/v1/kanji/検")).json()
    assert other["words"]["total"] == 1 and other["words"]["items"][0]["id"] == word.id


async def test_manual_entry_crud_visibility_validation_conflicts(authorized, seeded, db):
    client, _ = authorized
    user = await current_user(db, client.headers["authorization"][7:])
    book = await textbooks.create_textbook(db, user, TextbookCreate(name="Manual"))
    lesson = await textbooks.ensure_lesson(db, user, book.id, 1)
    url = f"/api/v1/lessons/{lesson.id}/entries"
    payload = {
        "kanji": "腹痛",
        "kana": "ふくつう",
        "order_no": 1,
        "content": [{"type": "example", "ja": "{{腹痛}}。私。"}],
    }
    created = await client.post(url, json=payload)
    assert created.status_code == 201, created.text
    entry = created.json()
    endpoint = f"/api/v1/entries/{entry['id']}"
    assert "腹痛[ふくつう]" in entry["content"][0]["ja"]
    assert (await client.post(url, json=payload)).status_code == 409
    for bad in [
        {**payload, "word_id": entry["word_id"]},
        {**payload, "kana": "abc"},
        {**payload, "content": [{"type": "bogus"}]},
        {**payload, "content": [{"type": "note", "text": "あ" * 6000}]},
    ]:
        assert (await client.post(url, json=bad)).status_code == 422
    assert (await client.patch(endpoint, json={"content": payload["content"]})).status_code == 422
    assert (await client.patch(endpoint, json={"ifMatch": 1, "content": None})).status_code == 422
    changed = await client.patch(
        endpoint,
        json={
            "ifMatch": 1,
            "content": [{"type": "example", "ja": "猫がいる。"}],
            "auto_furigana": False,
            "order_no": 2,
        },
    )
    assert changed.status_code == 200 and changed.json()["version"] == 2
    assert changed.json()["content"][0]["ja"] == "猫がいる。"
    raw = (await client.get(endpoint + "?furigana=false")).json()
    assert raw["search_text"] == "猫がいる。"
    assert (await client.patch(endpoint, json={"ifMatch": 1, "order_no": 3})).status_code == 409
    assert (await client.patch(endpoint, json={"ifMatch": 2, "auto_furigana": True})).json()[
        "version"
    ] == 3
    old_headers = dict(client.headers)
    headers, _ = await auth(client, "manual-other@example.com")
    client.headers.update(headers)
    assert (
        await client.post(
            url, json={"word_id": entry["word_id"], "order_no": 1, "content": payload["content"]}
        )
    ).status_code == 404
    assert (await client.patch(endpoint, json={"ifMatch": 3, "order_no": 3})).status_code == 404
    assert (await client.delete(endpoint)).status_code == 404
    other_user = await current_user(db, client.headers["authorization"][7:])
    other_book = await textbooks.create_textbook(db, other_user, TextbookCreate(name="Other"))
    other_lesson = await textbooks.ensure_lesson(db, other_user, other_book.id, 1)
    other_url = f"/api/v1/lessons/{other_lesson.id}/entries"
    assert (
        await client.post(
            other_url,
            json={"word_id": entry["word_id"], "order_no": 1, "content": payload["content"]},
        )
    ).status_code == 404
    client.headers.update(old_headers)
    assert (await client.delete(endpoint)).status_code == 200
    assert (await client.delete(endpoint)).status_code == 404
