def breakdown(text: str, readings: dict[str, list[str]], sources=None) -> list[dict]:
    """Keep kanji in order, ignore kana/okurigana, choose the first Hán Việt reading."""
    chars = dict.fromkeys(c for c in text if "一" <= c <= "鿿")
    return [
        {
            "char": char,
            "hanviet": next(iter(readings.get(char, [])), ""),
            **({"hanviet_source": sources.get(char)} if sources is not None else {}),
        }
        for char in chars
    ]
