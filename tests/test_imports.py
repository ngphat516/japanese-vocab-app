import pytest
from sqlalchemy import func, select

from app.modules.dictionary.models import Word
from app.modules.imports.models import ImportRow
from app.modules.textbooks.models import Entry
from tests.conftest import FIXTURES, auth


async def upload(client, book_id, name="mimikara.csv", adapter="mimikara", payload=None):
    return await client.post(
        "/api/v1/imports",
        data={"textbook_id": str(book_id), "adapter": adapter},
        files={"file": (name, payload if payload is not None else (FIXTURES / name).read_bytes())},
    )


@pytest.fixture
async def staged(authorized, seeded):
    client, _ = authorized
    book = (
        await client.post("/api/v1/textbooks", json={"name": "Import fixture", "edition": "old"})
    ).json()
    response = await upload(client, book["id"])
    assert response.status_code == 201, response.text
    return client, book, response.json()


async def test_IMP_01_adapter_registry(authorized):
    client, _ = authorized
    assert {x["name"] for x in (await client.get("/api/v1/imports/adapters")).json()} == {
        "mimikara",
        "csv_template",
    }


async def test_IMP_02_mimikara_edition(staged):
    client, book, job = staged
    rows = (await client.get(f"/api/v1/imports/{job['id']}/rows")).json()["items"]
    assert rows[0]["order_no"] == 357 and rows[0]["lesson_no"] == 5
    assert len(rows[0]["content"]) == 7
    await client.patch(f"/api/v1/textbooks/{book['id']}", json={"edition": "改訂版"})
    assert (await upload(client, book["id"])).status_code == 201


async def test_IMP_03_csv_template(authorized, seeded):
    client, _ = authorized
    template = await client.get("/api/v1/imports/template")
    assert "meaning_en" in template.text
    book = (await client.post("/api/v1/textbooks", json={"name": "CSV"})).json()
    result = await upload(client, book["id"], "template.csv", "csv_template")
    assert result.status_code == 201
    assert result.json()["total"] == 2
    assert (await client.post(f"/api/v1/imports/{result.json()['id']}/commit")).json()[
        "status"
    ] == "done"


async def test_IMP_04_validation_limits(authorized):
    client, _ = authorized
    book = (await client.post("/api/v1/textbooks", json={"name": "Validation"})).json()
    for name, payload, status in [
        ("bad.txt", b"x", 422),
        ("bad.csv", b"a,b\n1,2", 422),
        ("big.csv", b"x" * (5 * 1024 * 1024 + 1), 413),
        ("rows.csv", b"lesson,order,kanji,kana,meaning_vi\n" + b"1,1,,a,x\n" * 5001, 422),
        ("invalid.csv", b"lesson,order,kanji,kana,meaning_vi\n1,1,,a,\n", 422),
    ]:
        response = await upload(client, book["id"], name, "csv_template", payload)
        assert response.status_code == status, response.text
        assert "error" in response.json()
    assert (await upload(client, book["id"], "template.csv", "unknown")).status_code == 422


async def test_IMP_05_staging_lessons(staged):
    client, book, job = staged
    assert job["status"] == "review" and job["total"] == 3
    assert len((await client.get(f"/api/v1/textbooks/{book['id']}/lessons")).json()) == 2
    assert (await client.get(f"/api/v1/imports/{job['id']}/rows")).json()["total"] == 3


async def test_IMP_06_matching_states(staged):
    client, _, job = staged
    rows = (await client.get(f"/api/v1/imports/{job['id']}/rows")).json()["items"]
    assert [r["match_status"] for r in rows] == ["auto", "ambiguous", "none"]
    assert len(rows[1]["candidate_word_ids"]) == 3


async def test_IMP_07_review_choose_skip_private(staged):
    client, _, job = staged
    url = f"/api/v1/imports/{job['id']}"
    assert (await client.post(url + "/commit")).status_code == 409
    row = (await client.get(url + "/rows?match_status=ambiguous")).json()["items"][0]
    assert (
        await client.patch(url + f"/rows/{row['id']}", json={"chosen_word_id": 999999})
    ).status_code == 422
    assert (await client.patch(url + f"/rows/{row['id']}", json={"skipped": True})).json()[
        "match_status"
    ] == "skipped"
    assert (await client.post(url + "/commit")).json()["status"] == "done"
    assert (await client.post(url + "/commit")).status_code == 409
    assert (
        await client.patch(url + f"/rows/{row['id']}", json={"skipped": True})
    ).status_code == 409
    headers, _ = await auth(client, "b@example.com")
    client.headers.update(headers)
    assert (await client.get(url)).status_code == 404
    assert (await client.get(url + "/rows")).status_code == 404
    assert (await client.post(url + "/commit")).status_code == 404


async def test_IMP_08_atomic_rollback(staged, db):
    client, _, job = staged
    url = f"/api/v1/imports/{job['id']}"
    rows = (
        await db.scalars(
            select(ImportRow).where(ImportRow.job_id == job["id"]).order_by(ImportRow.row_no)
        )
    ).all()
    rows[1].match_status = "skipped"
    # The first row writes an entry; the last fails content validation inside commit.
    rows[2].content = [{"type": "example"}]
    await db.flush()
    words_before = await db.scalar(select(func.count()).select_from(Word))
    result = await client.post(url + "/commit")
    assert result.status_code == 409, result.text
    assert result.json()["error"]["details"]["status"] == "failed", result.text
    assert await db.scalar(select(func.count()).select_from(Entry)) == 0
    assert await db.scalar(select(func.count()).select_from(Word)) == words_before
    assert (await client.get(url)).json()["status"] == "failed"


async def test_IMP_09_raw_preservation(imported):
    client, _, job = imported
    row = (await client.get(f"/api/v1/imports/{job['id']}/rows")).json()["items"][0]
    assert row["raw"]["audio"] == "invented.mp3"
    blocks = (await client.get("/api/v1/search?q=きんちょう")).json()["items"][0]["entries"][0][
        "content"
    ]
    assert next(b for b in blocks if b["type"] == "raw")["data"]["audio"] == "invented.mp3"
