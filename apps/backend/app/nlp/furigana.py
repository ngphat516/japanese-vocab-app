import re
from copy import deepcopy
from functools import cache

from app.nlp.normalize import kana_normalize
from app.nlp.tokenizer import tokenize

_HAN = r"一-鿿㐀-䶿豈-﫿々\U00020000-\U000323af"
_PROTECTED = re.compile(r"[" + _HAN + r"ぁ-ヿ]+\[[ぁ-ゖァ-ヺー\s]+\]", re.DOTALL)
# Reviewed readings supplied for M4. Entry/textbook readings take precedence.
READING_OVERRIDES = {"私": "わたし", "腹痛": "ふくつう"}


def japanese_strings(content: list[dict]):
    """Only Japanese fields defined by the block contract, in source order."""
    for block in content:
        if block.get("type") == "example":
            yield block.get("ja", "")
        elif block.get("type") == "usage":
            yield block.get("context") or ""
            for variant in block.get("variants", []):
                yield variant.get("ja", "")
        elif block.get("type") == "collocation":
            yield from block.get("items", [])


def _annotate(surface: str, reading: str) -> str:
    if not re.search("[" + _HAN + "]", surface) or not reading:
        return surface
    groups = re.findall("[" + _HAN + "]+|[^" + _HAN + "]+", surface)

    @cache
    def align(index, offset):
        if index == len(groups):
            return ((),) if offset == len(reading) else ()
        group = groups[index]
        if not re.fullmatch("[" + _HAN + "]+", group):
            kana = kana_normalize(group)
            if not kana or not reading.startswith(kana, offset):
                return ()
            return tuple((group, *rest) for rest in align(index + 1, offset + len(kana)))
        solutions = []
        for end in range(offset + 1, len(reading) + 1):
            for rest in align(index + 1, end):
                solutions.append((f"{group}[{reading[offset:end]}]", *rest))
                if len(solutions) == 2:
                    return tuple(solutions)
        return tuple(solutions)

    solutions = align(0, 0)
    # Only a unique alignment may split readings between kanji runs.
    return "".join(solutions[0]) if len(solutions) == 1 else f"{surface}[{reading}]"


def add_furigana(text: str, readings: dict[str, str] | None = None) -> str:
    readings = {**READING_OVERRIDES, **(readings or {})}

    def annotate_plain(value):
        return "".join(
            _annotate(t.surface, kana_normalize(readings.get(t.surface, t.reading)))
            for t in tokenize(value)
        )

    result, start = [], 0
    for match in _PROTECTED.finditer(text):
        result.extend((annotate_plain(text[start : match.start()]), match.group()))
        start = match.end()
    result.append(annotate_plain(text[start:]))
    return "".join(result)


def content_furigana(content: list[dict], readings: dict[str, str]) -> list[dict]:
    result = deepcopy(content)
    for block in result:
        if block["type"] == "example":
            block["ja"] = add_furigana(block["ja"], readings)
        elif block["type"] == "usage":
            if block.get("context"):
                block["context"] = add_furigana(block["context"], readings)
            for variant in block.get("variants", []):
                variant["ja"] = add_furigana(variant["ja"], readings)
        elif block["type"] == "collocation":
            block["items"] = [add_furigana(item, readings) for item in block["items"]]
    return result


def strip_markup(value: str) -> str:
    return re.sub(r"\[[ぁ-ゖァ-ヺー\s]+\]", "", value).replace("{{", "").replace("}}", "")


def search_text(content: list[dict]) -> str:
    def walk(value):
        if isinstance(value, str):
            yield strip_markup(value)
        elif isinstance(value, dict):
            for key, item in value.items():
                if key != "type":
                    yield from walk(item)
        elif isinstance(value, list):
            for item in value:
                yield from walk(item)

    return " ".join(walk(content))
