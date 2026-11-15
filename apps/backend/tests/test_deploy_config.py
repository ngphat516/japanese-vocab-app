import pytest

from app.core.config import Settings, to_asyncpg_url, to_libpq_url

SECRET = "x" * 32


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        (
            "postgresql://u:p@ep-x.aws.neon.tech/vocab?sslmode=require&channel_binding=require",
            "postgresql+asyncpg://u:p@ep-x.aws.neon.tech/vocab?ssl=require",
        ),
        ("postgres://u:p@host:5432/db", "postgresql+asyncpg://u:p@host:5432/db"),
        (
            "postgresql+asyncpg://vocab:vocab@localhost:5432/vocab",
            "postgresql+asyncpg://vocab:vocab@localhost:5432/vocab",
        ),
        ("sqlite+aiosqlite:///x.db", "sqlite+aiosqlite:///x.db"),
    ],
)
def test_hosted_database_urls_are_normalized_for_asyncpg(source, expected):
    assert to_asyncpg_url(source) == expected
    assert Settings(database_url=source, jwt_secret=SECRET).database_url == expected


def test_worker_url_maps_asyncpg_ssl_back_to_libpq():
    url = to_asyncpg_url("postgresql://u:p@h/db?sslmode=require&channel_binding=require")
    assert to_libpq_url(url) == "postgresql://u:p@h/db?sslmode=require"
    assert to_libpq_url("postgresql+asyncpg://u:p@h/db") == "postgresql://u:p@h/db"
