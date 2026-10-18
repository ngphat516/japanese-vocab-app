import re
import unicodedata
from functools import lru_cache

import jaconv
import romkan2
from pykakasi import kakasi


def kana_normalize(text: str) -> str:
    value = jaconv.kata2hira(unicodedata.normalize("NFKC", text))
    return "".join(c for c in value if "ぁ" <= c <= "ゖ" or c == "ー")


def romaji_to_kana(text: str) -> str:
    return romkan2.to_hiragana(text.lower().replace(" ", ""))


@lru_cache(maxsize=1)
def _converter():
    return kakasi()


def to_romaji(text: str) -> str:
    return "".join(part["hepburn"] for part in _converter().convert(kana_normalize(text)))


def query_type(text: str) -> str:
    if any("一" <= c <= "鿿" or "㐀" <= c <= "䶿" for c in text):
        return "kanji"
    value = text.replace(" ", "")
    if value and all("ぁ" <= c <= "ヿ" or c == "ー" for c in value):
        return "kana"
    return "latin"


def normalize_query(text: str) -> str:
    kind = query_type(text)
    if kind == "kanji":
        return re.sub(r"\s+", "", unicodedata.normalize("NFKC", text))
    if kind == "kana":
        return kana_normalize(text)
    if kind == "latin" and re.fullmatch(r"[a-zA-Z ]+", text):
        converted = romaji_to_kana(text)
        if not re.search("[a-zA-Z]", converted):
            return kana_normalize(converted)
    return unicodedata.normalize("NFKC", text).strip().lower()
