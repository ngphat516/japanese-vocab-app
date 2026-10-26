from typing import Literal

from pydantic import BaseModel

from app.modules.textbooks.blocks import Block


class KanjiPart(BaseModel):
    char: str
    hanviet: str


class WordSummary(BaseModel):
    id: int
    kanji: str
    kana: str
    romaji: str
    jlpt_level: str | None
    hanviet: str
    kanji_breakdown: list[KanjiPart]
    saved: bool = False


class EntryResult(BaseModel):
    textbook: str
    textbook_id: int
    lesson: str
    order_no: int
    content: list[Block] | None
    summary: str


class WordEntries(BaseModel):
    word: WordSummary
    entries: list[EntryResult]


class ExampleCount(BaseModel):
    count: int
    capped: bool


class SearchItem(WordEntries):
    matched_by: Literal["exact", "lemma", "prefix", "meaning"] = "meaning"
    appears_in_examples: ExampleCount | None = None


class SearchResult(BaseModel):
    items: list[SearchItem]
    page: int
    size: int
    total: int
    total_capped: bool = False


class WordDetail(WordEntries):
    senses: list[dict]


class ExampleItem(BaseModel):
    ja: str
    vi: str | None
    textbook: str
    textbook_id: int
    lesson: str
    lesson_id: int
    order_no: int
    entry_id: int
    source_word: WordSummary
    ocr_review_required: bool


class ExamplesResult(BaseModel):
    items: list[ExampleItem]
    page: int
    size: int
    total: int
