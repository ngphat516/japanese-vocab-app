def breakdown(text: str, readings: dict[str, list[str]]) -> list[dict[str, str]]:
    """Keep kanji in order, ignore kana/okurigana, choose the first Hán Việt reading."""
    chars = dict.fromkeys(c for c in text if "一" <= c <= "鿿")
    return [{"char": char, "hanviet": next(iter(readings.get(char, [])), "")} for char in chars]
