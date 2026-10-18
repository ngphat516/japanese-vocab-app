import io
import json

import pytest

from app.core.exceptions import AppError
from app.modules.imports.adapters.normalized_json import NormalizedJSONAdapter


def document():
    return {
        "source": {"file": "invented-scan.pdf"},
        "rows": [
            {
                "kanji": "緊張",
                "kana": "きんちょう",
                "lesson_no": 1,
                "order_no": 1,
                "content": [
                    {"type": "meaning", "en": "tension"},
                    {"type": "example", "ja": "{{緊張[きんちょう]する}}"},
                    {"type": "raw", "data": {"pdf_page": 9, "ocr_review": True}},
                ],
                "raw": {"pdf_page": 9},
                "extra_source_field": "preserve",
            }
        ],
    }


def test_normalized_json_full_blocks_and_provenance():
    rows = NormalizedJSONAdapter().parse(io.BytesIO(json.dumps(document()).encode()))
    assert len(rows) == 1
    assert rows[0].content[0].en == "tension"
    assert rows[0].raw == {
        "pdf_page": 9,
        "source": {"file": "invented-scan.pdf"},
        "extra_source_field": "preserve",
    }


@pytest.mark.parametrize(
    ("payload", "error_type"),
    [(b"[]", TypeError), (b"{}", TypeError), (b"{bad", ValueError), (b'{"rows":[1]}', TypeError)],
)
def test_normalized_json_invalid_shape(payload, error_type):
    with pytest.raises(error_type):
        NormalizedJSONAdapter().parse(io.BytesIO(payload))


@pytest.mark.parametrize(
    ("payload", "code"),
    [
        (b"x" * (5 * 1024 * 1024 + 1), "IMPORT_FILE_TOO_LARGE"),
        (b'{"rows":[]}', "IMPORT_EMPTY"),
        (json.dumps({"rows": [{}] * 5001}).encode(), "IMPORT_TOO_MANY_ROWS"),
    ],
    ids=["file_size", "empty", "row_limit"],
)
def test_normalized_json_limits(payload, code):
    with pytest.raises(AppError) as error:
        NormalizedJSONAdapter().parse(io.BytesIO(payload))
    assert error.value.code == code


async def test_IMP_01_normalized_json_pipeline(authorized):
    client, _ = authorized
    book = (await client.post("/api/v1/textbooks", json={"name": "Invented OCR source"})).json()
    response = await client.post(
        "/api/v1/imports",
        data={"adapter": "normalized_json", "textbook_id": str(book["id"])},
        files={"file": ("invented.json", json.dumps(document()).encode(), "application/json")},
    )
    assert response.status_code == 201, response.text
    job = response.json()
    committed = await client.post(f"/api/v1/imports/{job['id']}/commit")
    assert committed.json()["status"] == "done", committed.text
    result = (await client.get("/api/v1/search?q=きんちょう")).json()["items"][0]
    assert result["entries"][0]["content"][0]["en"] == "tension"
    assert result["entries"][0]["content"][2]["data"]["pdf_page"] == 9
