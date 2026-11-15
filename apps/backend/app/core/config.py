from functools import lru_cache
from pathlib import Path
from typing import Literal
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# libpq-only parameters that asyncpg rejects; sslmode is mapped to asyncpg's ssl.
_LIBPQ_ONLY = {"channel_binding", "gssencmode", "target_session_attrs"}


def to_asyncpg_url(url: str) -> str:
    """Accept hosted-Postgres URLs (postgres://, postgresql://, ?sslmode=) for asyncpg."""
    parts = urlsplit(url)
    scheme = parts.scheme
    if scheme in {"postgres", "postgresql"}:
        scheme = "postgresql+asyncpg"
    if scheme != "postgresql+asyncpg":
        return url
    query = []
    for key, value in parse_qsl(parts.query, keep_blank_values=True):
        if key in _LIBPQ_ONLY:
            continue
        query.append(("ssl" if key == "sslmode" else key, value))
    return urlunsplit((scheme, parts.netloc, parts.path, urlencode(query), parts.fragment))


def to_libpq_url(url: str) -> str:
    """Inverse for psycopg (Procrastinate worker): asyncpg ssl= becomes libpq sslmode=."""
    parts = urlsplit(url)
    scheme = "postgresql" if parts.scheme == "postgresql+asyncpg" else parts.scheme
    query = [
        ("sslmode" if key == "ssl" else key, value)
        for key, value in parse_qsl(parts.query, keep_blank_values=True)
    ]
    return urlunsplit((scheme, parts.netloc, parts.path, urlencode(query), parts.fragment))


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(Path(__file__).resolve().parents[2].parent.parent / ".env", ".env"),
        extra="ignore",
    )
    database_url: str = "postgresql+asyncpg://vocab:vocab@localhost:5432/vocab"
    jwt_secret: str = Field(min_length=32)
    cors_origins: list[str] = ["http://localhost:3000"]
    rate_limit_enabled: bool = True
    import_mode: Literal["sync", "async"] = "async"

    @field_validator("database_url")
    @classmethod
    def _normalize_database_url(cls, value: str) -> str:
        return to_asyncpg_url(value)


@lru_cache
def get_settings():
    return Settings()
