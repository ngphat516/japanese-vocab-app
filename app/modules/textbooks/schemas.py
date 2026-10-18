from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, HttpUrl

from .blocks import Content


class TextbookCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    publisher: str | None = Field(default=None, max_length=200)
    level: str | None = Field(default=None, max_length=30)
    edition: str | None = Field(default=None, max_length=100)
    visibility: Literal["private", "public"] = "private"
    license: str | None = Field(default=None, max_length=500)
    source_url: HttpUrl | None = None


class TextbookPatch(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    publisher: str | None = None
    level: str | None = None
    edition: str | None = None
    visibility: Literal["private", "public"] | None = None
    license: str | None = None
    source_url: HttpUrl | None = None


class TextbookOut(TextbookCreate):
    model_config = ConfigDict(from_attributes=True)
    id: int
    owner_id: int


class LessonCreate(BaseModel):
    number: int = Field(gt=0)
    title: str = Field(min_length=1, max_length=200)


class LessonPatch(BaseModel):
    number: int | None = Field(default=None, gt=0)
    title: str | None = Field(default=None, min_length=1, max_length=200)


class LessonOut(LessonCreate):
    model_config = ConfigDict(from_attributes=True)
    id: int
    textbook_id: int


class EntryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    word_id: int
    lesson_id: int
    order_no: int
    content: Content
    search_text: str
