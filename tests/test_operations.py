from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import async_sessionmaker

from app.core import rate_limit
from app.core.config import get_settings


async def test_NFR_06_search_rate_limit(authorized, seeded, db, monkeypatch):
    client, _ = authorized
    monkeypatch.setattr(get_settings(), "rate_limit_enabled", True)
    monkeypatch.setattr(
        rate_limit,
        "Session",
        async_sessionmaker(
            bind=db.bind, expire_on_commit=False, join_transaction_mode="create_savepoint"
        ),
    )

    # Freeze minute boundaries so the 61st request deterministically shares a bucket.
    class FixedTime:
        @staticmethod
        def now(tz):
            return datetime(2026, 10, 18, 0, 0, tzinfo=UTC)

    monkeypatch.setattr(rate_limit, "datetime", FixedTime)
    for _ in range(60):
        response = await client.get("/api/v1/search?q=緊張")
        assert response.status_code == 200
    response = await client.get("/api/v1/search?q=緊張")
    assert response.status_code == 429
    assert response.json()["error"]["code"] == "RATE_LIMITED"


async def test_NFR_06_auth_and_import_limit(authorized, db, monkeypatch):
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
            return datetime(2026, 10, 18, 0, 0, tzinfo=UTC)

    monkeypatch.setattr(rate_limit, "datetime", FixedTime)
    for _ in range(10):
        assert (
            await client.post("/api/v1/auth/refresh", json={"refresh_token": "invalid"})
        ).status_code == 401
        assert (await client.post("/api/v1/imports")).status_code == 422
    assert (
        await client.post("/api/v1/auth/refresh", json={"refresh_token": "invalid"})
    ).status_code == 429
    assert (await client.post("/api/v1/imports")).status_code == 429


async def test_NFR_07_cors(authorized):
    client, _ = authorized
    response = await client.options(
        "/api/v1/search",
        headers={"Origin": "https://evil.example", "Access-Control-Request-Method": "GET"},
    )
    assert "access-control-allow-origin" not in response.headers


async def test_NFR_15_search_gzip_and_payload_budget(imported):
    client, _, _ = imported
    response = await client.get("/api/v1/search?q=きんちょう", headers={"Accept-Encoding": "gzip"})
    assert response.status_code == 200
    assert response.headers["content-encoding"] == "gzip"
    assert len(response.content) <= 200_000
    assert len(response.json()["items"][0]["entries"][0]["content"]) == 7
