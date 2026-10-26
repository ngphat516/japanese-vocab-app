import json
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, model_validator

from app.nlp.normalize import kana_normalize

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
    version: int
    auto_furigana: bool


class EntryCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    word_id: int | None = Field(default=None, gt=0)
    kanji: str = Field(default="", max_length=200)
    kana: str | None = Field(default=None, min_length=1, max_length=200)
    order_no: int = Field(gt=0)
    content: Content
    auto_furigana: bool = True

    @model_validator(mode="after")
    def choose_word(self):
        if (
            len(
                json.dumps(
                    [b.model_dump(exclude_none=True) for b in self.content], ensure_ascii=False
                ).encode()
            )
            > 16000
        ):
            raise ValueError("Entry content exceeds 16 KB")
        if self.word_id is not None:
            if self.kana is not None or self.kanji:
                raise ValueError("Choose word_id OR kanji/kana")
        elif not self.kana or not kana_normalize(self.kana):
            raise ValueError("kana is required")
        return self


class EntryPatch(BaseModel):
    model_config = ConfigDict(extra="forbid")
    if_match: int = Field(alias="ifMatch", gt=0)
    order_no: int | None = Field(default=None, gt=0)
    content: Content | None = None
    auto_furigana: bool | None = None

    @model_validator(mode="after")
    def nonnull(self):
        if any(getattr(self, key) is None for key in self.model_fields_set):
            raise ValueError("Explicit null is not supported")
        return self
