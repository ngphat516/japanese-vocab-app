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


class SearchItem(BaseModel):
    word: WordSummary
    entries: list[EntryResult]


class SearchResult(BaseModel):
    items: list[SearchItem]
    page: int
    size: int
    total: int
    total_capped: bool = False


class WordDetail(SearchItem):
    senses: list[dict]
