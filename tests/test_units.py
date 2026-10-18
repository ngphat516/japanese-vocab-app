import io
from pathlib import Path

import pytest
from openpyxl import Workbook
from pydantic import ValidationError

from app.core.exceptions import AppError
from app.modules.imports.adapters.csv_template import CSVTemplateAdapter
from app.modules.imports.adapters.mimikara import MimikaraAdapter
from app.modules.textbooks.blocks import validate_content
from app.nlp.furigana import search_text, strip_markup
from app.nlp.normalize import kana_normalize, normalize_query, query_type, romaji_to_kana

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.mark.parametrize(
    ("source", "expected"),
    [("キンチョウ", "きんちょう"), (" ｶﾞｯｺｳ! ", "がっこう"), ("ゆるむ", "ゆるむ")],
)
def test_katakana_to_hiragana(source, expected):
    assert kana_normalize(source) == expected


def test_romaji_and_query_detection():
    assert romaji_to_kana("kinchou") == "きんちょう"
    assert normalize_query(" kinchou ") == "きんちょう"
    assert normalize_query("căng thẳng") == "căng thẳng"
    assert query_type("緊張する") == "kanji"
    assert query_type("キンチョウ") == "kana"
    assert query_type("căng thẳng") == "latin"
    assert normalize_query("キン チョウ") == "きんちょう"
    assert normalize_query("緊 張") == "緊張"


def test_all_block_types_and_markup():
    blocks = [
        {"type": "meaning", "vi": "nghĩa"},
        {"type": "example", "ja": "{{緊張[きんちょう]する}}"},
        {"type": "usage", "context": "今", "variants": [{"ja": "よい", "correct": True}]},
        {"type": "collocation", "items": ["緊張"]},
        *[
            {"type": t, "items": [{"text": "語", "word_id": 1}]}
            for t in ["synonym", "antonym", "related"]
        ],
        {"type": "note", "text": "記録"},
        {"type": "raw", "data": {"audio": "a.mp3"}},
    ]
    assert len(validate_content(blocks)) == 9
    assert strip_markup("漢字[かんじ]と{{緊張[きんちょう]する}}") == "漢字と緊張する"
    value = search_text(blocks)
    assert "緊張する" in value and "[" not in value and "{{" not in value
    assert "a.mp3" in value
    assert strip_markup("note[keep] {{漢字[かんじ]}}") == "note[keep] 漢字"


@pytest.mark.parametrize(
    "block",
    [
        {"type": "audio", "url": "x"},
        {"type": "example"},
        {"type": "meaning"},
        {"type": "usage", "variants": [{"ja": "x", "correct": "yes"}]},
        {"type": "note", "text": "x", "unknown": 1},
    ],
)
def test_invalid_block_rejected(block):
    with pytest.raises(ValidationError):
        validate_content([block])


def test_csv_adapter():
    with (FIXTURES / "template.csv").open("rb") as source:
        rows = CSVTemplateAdapter().parse(source)
    assert len(rows) == 2
    assert (rows[0].lesson_no, rows[0].order_no) == (1, 2)
    assert [b.type for b in rows[0].content] == ["meaning", "example", "note", "raw"]
    assert rows[0].content[-1].data == {"extra": "preserved"}


def test_mimikara_adapter():
    with (FIXTURES / "mimikara.csv").open("rb") as source:
        rows = MimikaraAdapter().parse(source)
    assert len(rows) == 3
    assert (rows[0].lesson_no, rows[0].order_no) == (5, 357)
    assert [b.type for b in rows[0].content] == [
        "meaning",
        "example",
        "usage",
        "collocation",
        "synonym",
        "antonym",
        "raw",
    ]
    assert rows[0].content[2].variants[1].correct is False
    assert rows[0].content[-1].data["audio"] == "invented.mp3"


def test_xlsx_adapter():
    book = Workbook()
    book.active.append(["lesson", "order", "kanji", "kana", "meaning_vi"])
    book.active.append([1, 3, "緊張", "きんちょう", "căng thẳng"])
    source = io.BytesIO()
    book.save(source)
    source.seek(0)
    source.name = "fixture.xlsx"
    rows = CSVTemplateAdapter().parse(source)
    assert (len(rows), rows[0].order_no) == (1, 3)


@pytest.mark.parametrize(
    ("name", "payload", "code"),
    [
        ("x.csv", b"a,b\n1,2", "IMPORT_COLUMNS"),
        ("x.txt", b"x", "IMPORT_FORMAT"),
        ("x.csv", b"X" * (5 * 1024 * 1024 + 1), "IMPORT_FILE_TOO_LARGE"),
        ("x.csv", b"\xff", "IMPORT_ENCODING"),
        ("x.xlsx", b"bad", "IMPORT_FORMAT"),
        ("x.csv", b"lesson,order,kanji,kana\n", "IMPORT_EMPTY"),
    ],
    ids=["columns", "format", "size", "encoding", "xlsx", "empty"],
)
def test_adapter_invalid_files(name, payload, code):
    source = io.BytesIO(payload)
    source.name = name
    with pytest.raises(AppError) as error:
        CSVTemplateAdapter().parse(source)
    assert error.value.code == code
