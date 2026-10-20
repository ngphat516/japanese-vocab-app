"""Lazy, process-local Sudachi core tokenizer. No database dependencies."""

import os
import threading
from dataclasses import dataclass

from app.nlp.normalize import kana_normalize

_lock = threading.Lock()
_dictionary = None
_tokenizer = None
_pid = None
_CONTENT_POS = {"名詞", "動詞", "形容詞", "形状詞", "副詞"}


@dataclass(frozen=True)
class Token:
    surface: str
    lemma: str
    reading: str
    pos: tuple[str, ...]


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
            )
            for m in _tokenizer.tokenize(text)
        ]


def lemmas(text: str) -> list[str]:
    # Keep する as a content verb; auxiliaries (助動詞) and particles are dropped.
    return list(
        dict.fromkeys(
            t.lemma
            for t in tokenize(text)
            if t.pos[0] in _CONTENT_POS and any(c.isalpha() for c in t.lemma)
        )
    )


def entry_lemmas(content: list[dict]) -> list[str]:
    from app.nlp.furigana import japanese_strings, strip_markup

    result = []
    for value in japanese_strings(content):
        result.extend(lemmas(strip_markup(value).replace("__", "")))
    return list(dict.fromkeys(result))
