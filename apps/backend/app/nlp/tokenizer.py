"""Lazy, process-local Sudachi core tokenizer. No database dependencies."""

import os
import threading
from dataclasses import dataclass
from functools import lru_cache

from app.nlp.normalize import kana_normalize

_lock = threading.Lock()
_dictionary = None
_tokenizer = None
_pid = None
_CONTENT_POS = {"名詞", "動詞", "形容詞", "形状詞", "副詞"}
FORMAL_NOUNS = frozenset(
    {
        "こと",
        "もの",
        "ため",
        "とき",
        "ほう",
        "つもり",
        "ところ",
        "わけ",
        "よう",
        "事",
        "物",
        "為",
        "時",
        "方",
        "積もり",
        "所",
        "訳",
        "様",
    }
)


@dataclass(frozen=True)
class Token:
    surface: str
    lemma: str
    reading: str
    pos: tuple[str, ...]
    normalized_form: str = ""


def tokenize(text: str) -> list[Token]:
    global _dictionary, _tokenizer, _pid
    if not text:
        return []
    # Sudachi Tokenizer is mutable; lock initialization AND tokenization. Convert
    # morphemes to independent immutable values before releasing the lock.
    with _lock:
        if _tokenizer is None or _pid != os.getpid():
            from sudachipy import dictionary, tokenizer

            _dictionary = dictionary.Dictionary(dict="core")
            _tokenizer = _dictionary.tokenizer(tokenizer.Tokenizer.SplitMode.C)
            _pid = os.getpid()
        return [
            Token(
                m.surface(),
                m.dictionary_form(),
                kana_normalize(m.reading_form()),
                tuple(m.part_of_speech()),
                m.normalized_form(),
            )
            for m in _tokenizer.tokenize(text)
        ]


@lru_cache(maxsize=8192)
def lemma_reading(form: str) -> str:
    # Read the dictionary form, never the inflected surface (飲み -> のむ).
    return "".join(t.reading for t in tokenize(form))


def prohibitive(tokens: list[Token], index: int) -> bool:
    token = tokens[index]
    if token.lemma not in {"いける", "行ける", "なる", "だめ", "駄目"}:
        return False
    if token.lemma not in {"だめ", "駄目"} and "非自立可能" not in token.pos:
        return False
    before = tokens[:index]
    if not before:
        return False
    last = before[-1]
    if last.pos[0] == "助詞" and last.surface in {"は", "も"}:
        before = before[:-1]
        if not before:
            return False
        last = before[-1]
    if last.pos[:2] == ("助詞", "接続助詞") and last.surface in {
        "て",
        "で",
        "ては",
        "では",
        "ても",
        "でも",
    }:
        return True
    return (
        len(before) >= 2
        and last.pos[0] == "助詞"
        and last.surface in {"ば", "と"}
        and before[-2].lemma == "ない"
        and before[-2].pos[0] == "助動詞"
    )


def content_tokens(tokens: list[Token]):
    """Shared M2/M3 POS and contextual auxiliary filter, retaining token indices."""
    for index, token in enumerate(tokens):
        if token.pos[0] not in _CONTENT_POS or not any(c.isalpha() for c in token.lemma):
            continue
        if prohibitive(tokens, index):
            continue
        dependent = "非自立可能" in token.pos
        previous = tokens[index - 1] if index else None
        if token.lemma == "ござる" or (dependent and token.lemma == "ない"):
            continue
        if dependent and token.pos[0] in {"動詞", "形容詞"} and previous:
            # Sudachi can combine て+は into a single particle.
            after_te = previous.pos[:2] == ("助詞", "接続助詞") and previous.surface in {
                "て",
                "で",
                "ては",
                "では",
            }
            polite_request = token.lemma == "くださる" and previous.pos[0] in {"動詞", "名詞"}
            if token.lemma != "する" and (after_te or polite_request):
                continue
        yield index, token


def lemmas(text: str) -> list[str]:
    result = []
    for _, token in content_tokens(tokenize(text)):
        reading = lemma_reading(token.lemma)
        result.append(token.lemma)
        if token.normalized_form and reading and lemma_reading(token.normalized_form) == reading:
            result.append(token.normalized_form)
        if reading:
            result.append(reading)
    return list(dict.fromkeys(result))


def entry_lemmas(content: list[dict]) -> list[str]:
    from app.nlp.furigana import japanese_strings, strip_markup

    result = []
    for value in japanese_strings(content):
        result.extend(lemmas(strip_markup(value).replace("__", "")))
    return list(dict.fromkeys(result))


def example_lemmas(content: list[dict]) -> list[str]:
    return entry_lemmas([b for b in content if b.get("type") in {"example", "usage"}])
