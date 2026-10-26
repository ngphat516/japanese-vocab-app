import codecs
import csv
import io
import json
import sqlite3
import zipfile
from contextlib import closing
from datetime import UTC, datetime

import pytest
import yaml
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.core import rate_limit
from app.core.config import get_settings
from app.modules.auth.service import current_user
from app.modules.notebook.exports import (
    ANKI_DECK_ID,
    ANKI_FIELDS,
    ANKI_MODEL_ID,
    CSV_COLUMNS,
    markdown_bytes,
)
from app.modules.textbooks import service as textbooks
from tests.conftest import auth


def read_apkg(content, tmp_path):
    with zipfile.ZipFile(io.BytesIO(content)) as archive:
        assert set(archive.namelist()) == {"collection.anki2", "media"}
        assert json.loads(archive.read("media")) == {}
        path = tmp_path / "notes.sqlite"
        path.write_bytes(archive.read("collection.anki2"))
    with closing(sqlite3.connect(path)) as connection:
        notes = connection.execute("SELECT guid,flds,tags FROM notes ORDER BY id").fetchall()
        assert connection.execute("SELECT count(*) FROM cards").fetchone()[0] == len(notes)
        models, decks = connection.execute("SELECT models,decks FROM col").fetchone()
    return notes, json.loads(models), json.loads(decks)


def read_markdown(content):
    with zipfile.ZipFile(io.BytesIO(content)) as archive:
        rows = []
        for name in archive.namelist():
            assert "/" not in name and "\\" not in name and name.endswith(".md")
            assert not any(c in name for c in '<>:"|?*')
            text = archive.read(name).decode("utf-8")
            _, front, body = text.split("---", 2)
            rows.append((name, yaml.safe_load(front), body))
    return rows


async def test_m3_export_full_flow_and_round_trip(imported, db, tmp_path):
    client, book, _ = imported
    word_id = (await client.get("/api/v1/search?q=緊張して")).json()["items"][0]["word"]["id"]
    await client.get(f"/api/v1/words/{word_id}")
    assert (await client.get("/api/v1/history")).json()["total"] == 1
    user = await current_user(db, client.headers["authorization"][7:])
    lesson = await textbooks.ensure_lesson(db, user, book["id"], 99)
    await textbooks.save_entry(
        db,
        user,
        lesson.id,
        word_id,
        5,
        [
            {"type": "meaning", "vi": "nghĩa ưu tiên tiếng Việt"},
            {"type": "example", "ja": "{{緊張[きんちょう]}}した。", "vi": "Đã căng thẳng."},
            {"type": "example", "ja": "緊張している。"},
            {"type": "example", "ja": "緊張します。"},
        ],
    )
    saved = (
        await client.post(
            "/api/v1/saved-words",
            json={"word_id": word_id, "note": "<script>test</script>", "tags": ["kiểm tra"]},
        )
    ).json()
    collection = (await client.post("/api/v1/collections", json={"name": "Export"})).json()
    await client.post(
        f"/api/v1/collections/{collection['id']}/words", json={"saved_word_ids": [saved["id"]]}
    )
    assert (await client.get("/api/v1/search?q=緊張")).json()["items"][0]["word"]["saved"] is True
    for format in ["anki", "csv", "markdown"]:
        response = await client.get(
            "/api/v1/saved-words/export",
            params={
                "format": format,
                "collection_id": collection["id"],
                "tag": "kiểm tra",
                "jlpt": "N3",
            },
        )
        assert response.status_code == 200, (
            response.text[:200] if format == "csv" else response.status_code
        )
        assert "filename*=UTF-8''S%E1%BB%95%20t%E1%BB%AB" in response.headers["content-disposition"]
        if format == "anki":
            notes, models, decks = read_apkg(response.content, tmp_path)
            assert len(notes) == 1
            fields = notes[0][1].split("\x1f")
            assert len(fields) == 7 and fields[0] == "緊張"
            assert "nghĩa ưu tiên tiếng Việt" in fields[2]
            assert "{{" not in fields[4]
            assert "Tags: kiểm tra" in fields[5] and "<script>" not in fields[5]
            assert fields[5].startswith("JLPT: N3")
            assert str(ANKI_MODEL_ID) in models and str(ANKI_DECK_ID) in decks
            assert [f["name"] for f in models[str(ANKI_MODEL_ID)]["flds"]] == ANKI_FIELDS
            assert "{{furigana:" not in models[str(ANKI_MODEL_ID)]["tmpls"][0]["afmt"]
        elif format == "csv":
            assert response.content.startswith(codecs.BOM_UTF8)
            reader = csv.DictReader(io.StringIO(response.content.decode("utf-8-sig")))
            assert reader.fieldnames == CSV_COLUMNS
            rows = list(reader)
            assert len(rows) == 1 and rows[0]["Word"] == "緊張"
            assert "nghĩa ưu tiên tiếng Việt" in rows[0]["Meaning"]
            assert len(rows[0]["Examples"].split(" / ")) <= 2
        else:
            rows = read_markdown(response.content)
            assert len(rows) == 1
            assert {"word", "reading", "jlpt", "hanviet", "tags", "sources"} <= rows[0][1].keys()
            assert rows[0][1]["tags"] == ["kiểm tra"]
    await client.delete(f"/api/v1/saved-words/{saved['id']}")
    assert (await client.get("/api/v1/search?q=緊張")).json()["items"][0]["word"]["saved"] is False


@pytest.mark.parametrize("format", ["anki", "csv", "markdown"])
async def test_m3_export_empty_valid_file(authorized, format, tmp_path):
    client, _ = authorized
    response = await client.get("/api/v1/saved-words/export", params={"format": format})
    assert response.status_code == 200
    if format == "anki":
        assert len(read_apkg(response.content, tmp_path)[0]) == 0
    elif format == "csv":
        assert response.content.startswith(codecs.BOM_UTF8)
        assert list(csv.reader(io.StringIO(response.content.decode("utf-8-sig")))) == [CSV_COLUMNS]
    else:
        assert read_markdown(response.content) == []


@pytest.mark.parametrize("format", ["anki", "csv", "markdown"])
async def test_m3_export_ownership_and_filters(imported, format, tmp_path):
    client, _book, _ = imported
    word_id = (await client.get("/api/v1/search?q=緊張")).json()["items"][0]["word"]["id"]
    saved = (
        await client.post("/api/v1/saved-words", json={"word_id": word_id, "tags": ["A"]})
    ).json()
    collection = (await client.post("/api/v1/collections", json={"name": "A"})).json()
    await client.post(
        f"/api/v1/collections/{collection['id']}/words", json={"saved_word_ids": [saved["id"]]}
    )
    headers, _ = await auth(client, "export-b@example.com")
    client.headers.update(headers)
    assert (
        await client.get(
            "/api/v1/saved-words/export",
            params={"format": format, "collection_id": collection["id"]},
        )
    ).status_code == 404
    response = await client.get("/api/v1/saved-words/export", params={"format": format})
    assert response.status_code == 200
    if format == "anki":
        assert not read_apkg(response.content, tmp_path)[0]
    elif format == "csv":
        assert not list(csv.DictReader(io.StringIO(response.content.decode("utf-8-sig"))))
    else:
        assert not read_markdown(response.content)


async def test_m3_export_jmdict_fallback_safe_names_and_csv_cells(authorized, seeded, db, tmp_path):
    client, _ = authorized
    word_id = (await client.get("/api/v1/search?q=緊張")).json()["items"][0]["word"]["id"]
    await client.post("/api/v1/saved-words", json={"word_id": word_id, "note": '=HYPERLINK("x")'})
    csv_response = await client.get("/api/v1/saved-words/export?format=csv")
    row = next(iter(csv.DictReader(io.StringIO(csv_response.content.decode("utf-8-sig")))))
    assert (
        row["Notes"].startswith("'=")
        and "JMdict (" in row["MeaningSource"]
        and "tension" in row["Meaning"]
    )
    original = {
        "id": 1,
        "word": "橋",
        "reading": "はし",
        "jlpt": None,
        "hanviet": "KIỀU",
        "tags": [],
        "sources": [],
        "meaning": "Bridge",
        "examples": [],
        "note": "",
    }
    rows = [
        original,
        {**original, "id": 2, "word": "箸"},
        {**original, "id": 3, "word": "CON"},
        {**original, "id": 4, "word": "../a:b\\x?"},
        {**original, "id": 5, "word": "CON.txt"},
        {**original, "id": 6, "word": "LPT1.foo"},
    ]
    decoded = read_markdown(markdown_bytes(rows))
    assert len({name for name, _, _ in decoded}) == 6
    assert all(f"-{i}.md" in decoded[i - 1][0] for i in range(1, 7))
    assert all(decoded[i][0].startswith("_") for i in [2, 4, 5])
    # A dedicated example retains existing furigana inside the target marker.
    from app.modules.notebook.exports import anki_bytes

    original["examples"] = [{"ja": "{{橋[はし]}}を渡る。", "vi": "Qua cầu."}]
    fields = read_apkg(anki_bytes([original], 1), tmp_path)[0][0][1].split("\x1f")
    assert "<u><ruby>橋<rt>はし</rt></ruby></u>" in fields[4] and "{{" not in fields[4]
    guid = read_apkg(anki_bytes([original], 1), tmp_path)[0][0][0]
    original["note"] = "Changed note"
    assert read_apkg(anki_bytes([original], 1), tmp_path)[0][0][0] == guid


async def test_m3_export_rate_limit_per_user(authorized, db, monkeypatch):
    client, _ = authorized
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
            return datetime(2026, 10, 26, 0, 0, tzinfo=UTC)

    monkeypatch.setattr(rate_limit, "datetime", FixedTime)
    for _ in range(10):
        assert (await client.get("/api/v1/saved-words/export?format=csv")).status_code == 200
    assert (await client.get("/api/v1/saved-words/export?format=csv")).status_code == 429
    headers, _ = await auth(client, "rate-export-b@example.com")
    client.headers.update(headers)
    assert (await client.get("/api/v1/saved-words/export?format=csv")).status_code == 200


async def test_m3_export_auth_and_invalid_format(client, authorized):
    client, _ = authorized
    assert (await client.get("/api/v1/saved-words/export?format=pdf")).status_code == 422
    client.headers.pop("authorization")
    assert (await client.get("/api/v1/saved-words/export?format=csv")).status_code == 401
