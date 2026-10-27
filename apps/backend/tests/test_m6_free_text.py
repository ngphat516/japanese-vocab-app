import io
import json

from sqlalchemy import select

from app.modules.dictionary import service as dictionary
from app.modules.imports.adapters.free_text import FreeTextAdapter
from app.modules.textbooks.models import Entry
from tests.conftest import auth
from tests.test_m5_worker import drain, worker_env  # noqa: F401


def parse(text, **options):
    return FreeTextAdapter().parse(io.BytesIO(text.encode()), **options)


def test_IMP_12_token_positions_grouping_and_filters():
    rows = parse(
        "東京で猫が食べました。猫が食べて、また食べる！猫は食べなかった。これは一つのこと。"
    )
    keyed = {r.raw["normalized_form"]: r for r in rows}
    assert "東京" not in keyed and "事" not in keyed and "こと" not in keyed
    eating = keyed["食べる"]
    assert eating.kanji == "食べる" and eating.kana == "たべる"
    examples = [b.ja for b in eating.content if b.type == "example"]
    assert len(examples) == 2
    assert "{{食べ}}ました" in examples[0]
    assert "{{食べて}}" not in examples[1]  # particle て is outside the verb token
    assert "{{食べ}}て" in examples[1] and "{{食べる}}" in examples[1]
    assert all(b.type != "meaning" for r in rows for b in r.content)
    assert eating.content[0].data["sentences"][0] == "東京で猫が食べました。"
    assert "東京" in {
        r.raw["normalized_form"] for r in parse("東京へ行く。", include_proper_nouns=True)
    }
    assert [r.order_no for r in rows] == list(range(1, len(rows) + 1))


async def post_text(client, book, text="猫が食べました。", **options):
    return await client.post(
        "/api/v1/imports",
        data={"adapter": "free_text", "textbook_id": str(book["id"]), "text": text, **options},
    )


async def test_IMP_12_sync_matching_exclusion_commit_permissions(authorized, db):
    client, _ = authorized
    known = await dictionary.create_word(db, "猫", "ねこ")
    known.jlpt_level = "N5"
    await db.flush()
    book = (await client.post("/api/v1/textbooks", json={"name": "Self written text"})).json()
    result = await post_text(client, book, exclude_jlpt="N5,N4", lesson_no="3")
    assert result.status_code == 201, result.text
    url = f"/api/v1/imports/{result.json()['id']}"
    rows = (await client.get(url + "/rows")).json()["items"]
    cat = next(r for r in rows if r["kanji"] == "猫")
    assert cat["match_status"] == "skipped" and cat["raw"]["skip_reason"] == "EXCLUDED_JLPT"
    assert all(r["lesson_no"] == 3 for r in rows)
    assert (await client.post(url + "/commit")).json()["status"] == "done"
    entries = (await db.scalars(select(Entry))).all()
    assert len(entries) == 1 and entries[0].word_id != known.id
    assert "[た]" in json.dumps(entries[0].content_furigana, ensure_ascii=False)
    assert all(b["type"] != "meaning" for b in entries[0].content)
    headers, _ = await auth(client, "other-m6@example.com")
    client.headers.update(headers)
    assert (await client.get(url)).status_code == 404
    assert (await post_text(client, book)).status_code == 404


async def test_IMP_12_input_limits_txt_and_validation(authorized):
    client, _ = authorized
    book = (await client.post("/api/v1/textbooks", json={"name": "Validation"})).json()
    for value in ["猫" * 20001, "", "   "]:
        assert (await post_text(client, book, text=value)).status_code == 422
    assert (await post_text(client, book, exclude_jlpt="N6")).status_code == 422
    assert (await post_text(client, book, lesson_no="0")).status_code == 422
    for name, payload, status in [
        ("test.txt", "猫です。".encode(), 201),
        ("bad.txt", b"\xff", 422),
        ("bad.csv", b"cat", 422),
        ("large.txt", ("猫" * 20001).encode(), 422),
    ]:
        response = await client.post(
            "/api/v1/imports",
            data={"adapter": "free_text", "textbook_id": str(book["id"])},
            files={"file": (name, payload)},
        )
        assert response.status_code == status, response.text
    assert (await post_text(client, book, text="。！？\n")).status_code == 422


async def test_IMP_12_async_full_flow(worker_env):  # noqa: F811
    client, book, sessions, queue = worker_env
    result = await post_text(
        client, book, text="静かな部屋で本を読みました。明日も本を読む。", lesson_no="2"
    )
    assert result.status_code == 202
    assert (await post_text(client, book, text="猫" * 20001)).status_code == 422
    url = f"/api/v1/imports/{result.json()['id']}"
    await drain(queue)
    job = (await client.get(url)).json()
    assert job["status"] == "review" and job["total"] > 0
    assert (await client.post(url + "/commit")).status_code == 202
    await drain(queue)
    assert (await client.get(url)).json()["status"] == "done"
    async with sessions() as db:
        entries = (await db.scalars(select(Entry))).all()
        assert len(entries) == job["total"]
        assert all(e.content_furigana for e in entries)
