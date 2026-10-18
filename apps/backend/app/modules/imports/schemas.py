from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator

from app.modules.textbooks.blocks import Content
from app.nlp.normalize import kana_normalize


class NormalizedRow(BaseModel):
    kanji: str = ""
    kana: str = Field(min_length=1, max_length=200)
    lesson_no: int = Field(gt=0)
    order_no: int = Field(gt=0)
    content: Content
    raw: dict = Field(default_factory=dict)

    @field_validator("kana")
    @classmethod
    def valid_reading(cls, value):
        if not kana_normalize(value):
            raise ValueError("reading requires kana")
        return value


class RowReview(BaseModel):
    chosen_word_id: int | None = Field(default=None, gt=0)
    skipped: bool = False

    @model_validator(mode="after")
    def one_action(self):
        if self.skipped == (self.chosen_word_id is not None):
            raise ValueError("Choose a word OR skip the row")
        return self


MatchStatus = Literal["auto", "ambiguous", "none", "skipped"]
