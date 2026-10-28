"""Offline source projection and evaluation; no network or database side effects."""

import json
import unicodedata
from pathlib import Path

from app.nlp.vietnamese import normalize_tones
from scripts.build_hanviet_unihan import HAN, apply_overrides


def parse_kanjidic2(path):
    document = json.loads(Path(path).read_text(encoding="utf-8-sig"))
    result = {}
    for row in document["characters"]:
        char = row["literal"]
        if not HAN.fullmatch(char):
            continue
        values = list(
            dict.fromkeys(
                normalize_tones(reading["value"].strip()).upper()
                for group in (row.get("readingMeaning") or {}).get("groups", [])
                for reading in group.get("readings", [])
                if reading["type"] == "vietnam" and reading["value"].strip()
            )
        )
        if values:
            result[char] = values
    if not result:
        raise ValueError("No vietnam readings found in KANJIDIC2")
    return result


def score(source, standard):
    """All rates use the entire nonempty gold set, including source misses."""
    standard = {c: v for c, v in standard.items() if v}
    total = len(standard)
    counts = {
        "covered": sum(bool(source.get(c)) for c in standard),
        "first_match": sum(
            bool(source.get(c)) and source[c][0] == v[0] for c, v in standard.items()
        ),
        "contains_first": sum(v[0] in source.get(c, []) for c, v in standard.items()),
        "contains_all": sum(set(v) <= set(source.get(c, [])) for c, v in standard.items()),
    }
    return {
        "standard_characters": total,
        **counts,
        **{key + "_percent": 100 * n / total if total else 0 for key, n in counts.items()},
    }


def prefer_kanjidic2(scores):
    kanji, direct = scores["kanjidic2"], scores["unihan"]
    return kanji["first_match_percent"] >= 90 and kanji["first_match"] > direct["first_match"]


def score_iy_insensitive(source, standard):
    """Diagnostic only: preserve tone marks while folding I/Y, never modify data."""

    def fold(data):
        return {
            c: [
                unicodedata.normalize(
                    "NFC", unicodedata.normalize("NFD", v).upper().replace("Y", "I")
                )
                for v in values
            ]
            for c, values in data.items()
        }

    return score(fold(source), fold(standard))


def combine(direct, variants, kanjidic2, overrides, prefer):
    result = dict(variants)
    result.update({c: (v, "unihan") for c, v in direct.items()})
    if prefer:
        result.update({c: (v, "kanjidic2") for c, v in kanjidic2.items() if v})
    # Direct readings already take priority over variants. With a failed gate,
    # KANJIDIC2 is evaluation-only, preserving the previous source order.
    return apply_overrides(result, overrides)


def coverage(data, counts):
    return {
        "characters": len(counts),
        "covered": sum(bool(data.get(c)) for c in counts),
        "entry_weight": sum(counts.values()),
        "covered_entry_weight": sum(n for c, n in counts.items() if data.get(c)),
    }


def needs_review(current, kanjidic2, unihan):
    # Explicitly exclude agreement (same normalized reading set). A missing
    # source is not evidence of agreement or first-reading disagreement.
    if current and kanjidic2 and unihan and set(kanjidic2) == set(unihan):
        return False
    return (
        not current
        or bool(kanjidic2 and unihan and kanjidic2[0] != unihan[0])
        or max(len(current), len(kanjidic2), len(unihan)) >= 3
    )
