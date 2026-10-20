import asyncio
from concurrent.futures import ThreadPoolExecutor

import pytest

from app.nlp.furigana import _annotate, add_furigana
from app.nlp.tokenizer import entry_lemmas, lemmas, tokenize


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        ("行かなかった", ["行く"]),
        ("食べました", ["食べる"]),
        ("緊張して", ["緊張", "する"]),  # Keep する; it is a content verb.
        ("は、が、を、も。", []),
        ("、。 ! 123", []),
    ],
)
def test_content_lemmas(source, expected):
    assert lemmas(source) == expected


def test_tokens_readings_deduplication_and_thread_safety():
    tokens = tokenize("食べました")
    assert tokens[0].surface == "食べ"
    assert tokens[0].lemma == "食べる"
    assert tokens[0].reading == "たべ"
    assert isinstance(tokens[0].pos, tuple)
    assert lemmas("猫と猫") == ["猫"]
    with ThreadPoolExecutor(max_workers=10) as pool:
        assert list(pool.map(lemmas, ["行かなかった"] * 30)) == [["行く"]] * 30
    assert tokenize("") == []


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        ("食べる", "食[た]べる"),
        ("取り扱い", "取[と]り扱[あつか]い"),
        ("緊張して", "緊張[きんちょう]して"),
        ("人々", "人々[ひとびと]"),
        ("漢字[かんじ]と食[た]べる", "漢字[かんじ]と食[た]べる"),
        ("{{緊張して}}", "{{緊張して}}"),
        ("かな カナ ABC 123", "かな カナ ABC 123"),
        ("", ""),
    ],
)
def test_furigana_and_idempotence(source, expected):
    result = add_furigana(source)
    assert result == expected
    assert add_furigana(result) == result


def test_furigana_alignment_fallback_and_unknown_reading():
    assert _annotate("取り扱い", "ふめい") == "取り扱い[ふめい]"
    assert _annotate("漢あ字", "ああああ") == "漢あ字[ああああ]"  # Ambiguous anchors.
    assert _annotate("未知", "") == "未知"


def test_entry_lemmas_cover_only_japanese_block_fields():
    content = [
        {"type": "meaning", "vi": "猫"},
        {"type": "example", "ja": "{{行[い]かなかった}}", "vi": "犬"},
        {"type": "usage", "context": "食べました", "variants": [{"ja": "緊張して"}]},
        {"type": "collocation", "items": ["__と歩く"]},
    ]
    assert entry_lemmas(content) == ["行く", "食べる", "緊張", "する", "歩く"]


async def test_lazy_initialization_from_concurrent_threads(monkeypatch):
    from app.nlp import tokenizer

    monkeypatch.setattr(tokenizer, "_tokenizer", None)
    results = await asyncio.gather(*(asyncio.to_thread(tokenize, "猫") for _ in range(10)))
    assert all(result[0].lemma == "猫" for result in results)
