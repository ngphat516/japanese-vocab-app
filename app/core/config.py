from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    database_url: str = "postgresql+asyncpg://vocab:vocab@localhost:5432/vocab"
    jwt_secret: str = Field(min_length=32)
    cors_origins: list[str] = ["http://localhost:3000"]
    rate_limit_enabled: bool = True


@lru_cache
def get_settings():
    return Settings()
