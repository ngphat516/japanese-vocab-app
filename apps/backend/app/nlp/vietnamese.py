"""Pure Vietnamese tone placement; preserve spelling, case and i/y."""

import re
import unicodedata

TONES = frozenset("\u0300\u0301\u0303\u0309\u0323")


def normalize_tones(text: str) -> str:
    def syllable(match):
        letters, tone = [], ""
        for char in unicodedata.normalize("NFC", match[0]):
            parts = unicodedata.normalize("NFD", char)
            tone = next((c for c in parts if c in TONES), tone)
            letters.append(
                unicodedata.normalize("NFC", "".join(c for c in parts if c not in TONES))
            )
        vowels = [i for i, c in enumerate(letters) if c.lower() in "aăâeêioôơuưy"]
        if len(vowels) > 1 and "".join(letters[:2]).lower() in {"qu", "gi"}:
            vowels = [i for i in vowels if i != 1]
        if not tone or not vowels:
            return unicodedata.normalize("NFC", match[0])
        preferred = [i for i in vowels if letters[i].lower() in "êơ"]
        target = (
            preferred[-1]
            if preferred
            else vowels[1]
            if len(vowels) >= 3
            else vowels[-1]
            if vowels[-1] < len(letters) - 1
            else vowels[0]
        )
        letters[target] = unicodedata.normalize("NFC", letters[target] + tone)
        return "".join(letters)

    return re.sub(r"[^\W\d_]+", syllable, unicodedata.normalize("NFC", text))
