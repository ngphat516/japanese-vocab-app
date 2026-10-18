import os
import subprocess
from pathlib import Path

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from testcontainers.community.postgres import PostgresContainer

os.environ.setdefault("JWT_SECRET", "test-only-secret-with-at-least-32-characters")
os.environ["RATE_LIMIT_ENABLED"] = "false"

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture(scope="session")
def pg_url():
    # Deliberately fail when Docker is unavailable; never silently substitute SQLite or skip.
    with PostgresContainer("pgvector/pgvector:pg16", driver="psycopg2") as pg:
        url = pg.get_connection_url().replace("postgresql+psycopg2", "postgresql+asyncpg")
        env = {**os.environ, "DATABASE_URL": url}
        subprocess.run([os.sys.executable, "-m", "alembic", "upgrade", "head"], check=True, env=env)
        yield url


@pytest_asyncio.fixture
async def db(pg_url):
    engine = create_async_engine(pg_url)
    async with engine.connect() as connection:
        transaction = await connection.begin()
        async with AsyncSession(
            bind=connection, expire_on_commit=False, join_transaction_mode="create_savepoint"
        ) as session:
            yield session
        await transaction.rollback()
    await engine.dispose()


@pytest_asyncio.fixture
async def client(db):
    from app.db.session import get_db
    from app.main import app

    async def override_db():
        yield db

    app.dependency_overrides[get_db] = override_db
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as http:
        yield http
    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def seeded(db):
    from app.modules.dictionary import service

    await service.seed_kanjidic(db, FIXTURES / "kanjidic.json")
    await service.seed_jmdict(db, FIXTURES / "jmdict.json")
    await service.seed_hanviet(db, FIXTURES / "hanviet.csv")
    await service.seed_jlpt(db, FIXTURES / "jlpt.csv")
    await db.flush()
    return db


async def auth(client, email="a@example.com"):
    result = await client.post(
        "/api/v1/auth/register", json={"email": email, "password": "password123"}
    )
    assert result.status_code == 201, result.text
    response = await client.post(
        "/api/v1/auth/login", json={"email": email, "password": "password123"}
    )
    assert response.status_code == 200, response.text
    tokens = response.json()
    return {"Authorization": "Bearer " + tokens["access_token"]}, tokens


@pytest_asyncio.fixture
async def authorized(client):
    headers, tokens = await auth(client)
    client.headers.update(headers)
    return client, tokens


@pytest_asyncio.fixture
async def imported(authorized, seeded):
    client, _ = authorized
    book = (
        await client.post(
            "/api/v1/textbooks",
            json={
                "name": "Invented Mimikara",
                "edition": "改訂版",
                "license": "commercial private use",
            },
        )
    ).json()
    response = await client.post(
        "/api/v1/imports",
        data={"textbook_id": str(book["id"]), "adapter": "mimikara"},
        files={"file": ("mimikara.csv", (FIXTURES / "mimikara.csv").read_bytes(), "text/csv")},
    )
    assert response.status_code == 201, response.text
    job = response.json()
    rows = (await client.get(f"/api/v1/imports/{job['id']}/rows")).json()["items"]
    ambiguous = next(r for r in rows if r["match_status"] == "ambiguous")
    await client.patch(
        f"/api/v1/imports/{job['id']}/rows/{ambiguous['id']}",
        json={"chosen_word_id": ambiguous["candidate_word_ids"][0]},
    )
    response = await client.post(f"/api/v1/imports/{job['id']}/commit")
    assert response.json()["status"] == "done", response.text
    return client, book, job
