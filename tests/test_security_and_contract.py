from datetime import UTC, datetime, timedelta

import jwt
import pytest
from httpx import ASGITransport, AsyncClient

from app.core.config import get_settings
from app.core.exceptions import AppError
from app.core.security import decode, digest, token
from app.modules.textbooks.blocks import validate_content
from app.nlp.kanji import breakdown


def test_kanji_breakdown_ignores_okurigana():
    readings = {"緊": ["KHẨN"], "張": ["TRƯƠNG"], "楽": ["LẠC", "NHẠC"]}
    assert breakdown("緊張する", readings) == [
        {"char": "緊", "hanviet": "KHẨN"},
        {"char": "張", "hanviet": "TRƯƠNG"},
    ]
    assert breakdown("ゆるむ", readings) == []
    assert breakdown("楽", readings) == [{"char": "楽", "hanviet": "LẠC"}]


def test_tokens_are_typed_signed_and_expire():
    access, _ = token(7, "access")
    refresh, _ = token(7, "refresh")
    assert decode(access, "access")["sub"] == "7"
    assert decode(refresh, "refresh")["sub"] == "7"
    assert len(digest(refresh)) == 64
    with pytest.raises(AppError):
        decode(refresh, "access")
    with pytest.raises(AppError):
        decode(access + "broken", "access")
    expired = jwt.encode(
        {
            "sub": "7",
            "type": "access",
            "iat": datetime.now(UTC) - timedelta(hours=1),
            "exp": datetime.now(UTC) - timedelta(seconds=1),
            "jti": "old",
        },
        get_settings().jwt_secret,
        algorithm="HS256",
    )
    with pytest.raises(AppError):
        decode(expired, "access")


def test_raw_preserves_arbitrary_json():
    assert (
        validate_content([{"type": "raw", "data": ["opaque", {"nested": 1}]}])[0]["data"][1][
            "nested"
        ]
        == 1
    )


async def test_openapi_p0_contract_and_error_shape():
    from app.main import app

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        schema = (await client.get("/openapi.json")).json()
        assert "/api/v1/search" in schema["paths"]
        assert "/api/v1/imports/{job_id}/commit" in schema["paths"]
        assert "/api/v1/words/{word_id}" in schema["paths"]
        assert "/api/v1/study/items" not in schema["paths"]
        assert "post" not in schema["paths"]["/api/v1/lessons/{lesson_id}/entries"]
        for path in schema["paths"].values():
            for operation in path.values():
                if isinstance(operation, dict):
                    assert not {"request", "db", "user"} & {
                        p["name"] for p in operation.get("parameters", [])
                    }
        response = await client.get("/missing")
        assert response.status_code == 404
        assert set(response.json()["error"]) == {"code", "message", "details"}


def test_architecture_nlp_is_independent():
    import ast
    from pathlib import Path

    for file in Path("app/nlp").glob("*.py"):
        for node in ast.walk(ast.parse(file.read_text(encoding="utf-8-sig"))):
            if isinstance(node, ast.ImportFrom):
                assert not (node.module or "").startswith(("app.db", "app.modules"))


async def test_transaction_cleanup_error_prevents_success_response():
    from app.db.session import get_db
    from app.main import app

    class Probe:
        async def execute(self, statement):
            return None

    async def failing_transaction():
        yield Probe()
        raise RuntimeError("Simulated commit failure")

    app.dependency_overrides[get_db] = failing_transaction
    try:
        transport = ASGITransport(app=app, raise_app_exceptions=False)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/health")
            assert response.status_code == 500
            assert response.json()["error"]["code"] == "INTERNAL_ERROR"
            assert "Simulated" not in response.text
    finally:
        app.dependency_overrides.pop(get_db, None)
