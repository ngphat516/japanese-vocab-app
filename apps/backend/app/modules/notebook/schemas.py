import unicodedata
from datetime import datetime
from typing import Annotated, Literal

from pydantic import BaseModel, Field, field_validator

from app.modules.search.schemas import WordSummary

JLPT = Literal["N1", "N2", "N3", "N4", "N5", "none"]


def normalize_tag(value):
    return unicodedata.normalize("NFKC", value).strip()


def normalize_tags(values):
    values = list(dict.fromkeys(normalize_tag(v) for v in values if normalize_tag(v)))
    if len(values) > 20 or any(len(v) > 30 for v in values):
        raise ValueError("At most 20 tags, each at most 30 characters")
    return values


class SaveWord(BaseModel):
    word_id: int = Field(gt=0)
    note: str = Field(default="", max_length=10000)
    tags: list[str] = Field(default_factory=list)
    _tags = field_validator("tags")(normalize_tags)


class SavedPatch(BaseModel):
    note: str | None = Field(default=None, max_length=10000)
    tags: list[str] | None = None

    @field_validator("tags")
    @classmethod
    def tags_valid(cls, value):
        if value is None:
            raise ValueError("tags cannot be null")
        return normalize_tags(value)

    @field_validator("note")
    @classmethod
    def note_valid(cls, value):
        if value is None:
            raise ValueError("note cannot be null")
        return value


class CollectionInput(BaseModel):
    name: str = Field(min_length=1, max_length=100)

    @field_validator("name")
    @classmethod
    def name_valid(cls, value):
        value = normalize_tag(value)
        if not value or len(value) > 100:
            raise ValueError("Invalid collection name")
        return value


class CollectionMembers(BaseModel):
    saved_word_ids: Annotated[
        list[Annotated[int, Field(gt=0)]], Field(min_length=1, max_length=1000)
    ]


class Source(BaseModel):
    textbook_id: int
    textbook: str
    lesson_id: int
    lesson: str
    order_no: int


class SavedItem(BaseModel):
    id: int
    word: WordSummary
    note: str
    tags: list[str]
    created_at: datetime
    sources: list[Source]


class SavedPage(BaseModel):
    items: list[SavedItem]
    total: int
    page: int
    size: int


class HistoryItem(BaseModel):
    id: int
    word: WordSummary
    query: str
    searched_at: datetime
    sources: list[Source]


class HistoryPage(BaseModel):
    items: list[HistoryItem]
    total: int
    page: int
    size: int


class CollectionItem(BaseModel):
    id: int
    name: str
    created_at: datetime
    word_count: int


class CollectionPage(BaseModel):
    items: list[CollectionItem]
    total: int
    page: int
    size: int
