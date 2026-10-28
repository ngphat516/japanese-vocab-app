"""Read-only M7b experiment. Never writes production CSV/metadata or seeds the DB."""

import asyncio
import hashlib
import json
from collections import Counter
from pathlib import Path

from sqlalchemy import select

from app.db.session import engine
from app.modules.dictionary.models import Kanji, Word
from app.modules.textbooks.models import Entry
from app.nlp.furigana import japanese_strings
from app.nlp.hanviet import combined_readings as candidate_combined
from app.nlp.vietnamese import normalize_tones
from scripts.build_hanviet_m7 import KANJIDIC, OVERRIDES, READINGS, VARIANTS
from scripts.build_hanviet_unihan import HAN, apply_overrides, parse, parse_variants, with_variants
from scripts.hanviet_sources import coverage, parse_kanjidic2, score, score_iy_insensitive

REVIEWS = [Path("verification/m5_hanviet_review.md"), Path("verification/m6_hanviet_review_2.md")]


def reviewed_standard(paths, overrides, expected_batch_size=300):
    """Keep all reviewed characters, including explicit blank overrides."""
    result = {}
    for path in paths:
        batch = {}
        for line in path.read_text(encoding="utf-8-sig").splitlines():
            cells = [v.strip() for v in line.split("|")]
            if len(cells) < 4 or not HAN.fullmatch(cells[1]):
                continue
            char = cells[1]
            if char in result or char in batch:
                raise ValueError(f"Duplicate reviewed character: {char}")
            values = (
                list(overrides[char][0])
                if char in overrides
                else list(
                    dict.fromkeys(
                        normalize_tones(v.strip()).upper()
                        for v in cells[2].split("/")
                        if v.strip() not in {"", "—"}
                    )
                )
            )
            batch[char] = values
        if len(batch) != expected_batch_size:
            raise ValueError(f"Expected {expected_batch_size} reviewed characters in {path}")
        result.update(batch)
    return result


def passes_gate(combined, current):
    return (
        combined["first_match_percent"] >= 95
        and combined["first_match_percent"] > current["first_match_percent"]
    )


async def evaluate():
    header = json.loads(KANJIDIC.read_text(encoding="utf-8-sig"))
    if header["version"] != "3.6.2" or header["dictDate"] != "2026-10-19":
        raise ValueError("KANJIDIC2 does not match the pinned M7 source")
    members = {r["literal"] for r in header["characters"]}
    kanjidic = parse_kanjidic2(KANJIDIC)
    unihan = with_variants(parse(READINGS), parse_variants(VARIANTS))
    overrides = apply_overrides({}, OVERRIDES)
    gold_all = reviewed_standard(REVIEWS, overrides)
    gold = {c: v for c, v in gold_all.items() if c in members}
    combined = candidate_combined(members, kanjidic, unihan)
    proposed = apply_overrides(combined, OVERRIDES)
    strategies = {
        "unihan_current": {c: v for c, (v, _) in apply_overrides(unihan, OVERRIDES).items()},
        "kanjidic2": kanjidic,
        "combined": {c: v for c, (v, _) in combined.items()},
        "combined_override": {c: v for c, (v, _) in proposed.items()},
    }
    scores = {s: score(data, gold) for s, data in strategies.items()}
    raw_unihan = score({c: v for c, (v, _) in unihan.items()}, gold)
    async with engine.connect() as db:
        rows = (
            await db.execute(
                select(Word.kanji, Entry.content).join(Entry, Entry.word_id == Word.id)
            )
        ).all()
        current = dict((await db.execute(select(Kanji.char, Kanji.hanviet))).all())
    await engine.dispose()
    counts = Counter()
    for word, content in rows:
        counts.update(set(HAN.findall(word + " " + " ".join(japanese_strings(content)))))
    eligible = {c: n for c, n in counts.items() if c in members}
    excluded = sorted(counts.keys() - members)
    accepted = passes_gate(scores["combined"], scores["unihan_current"])
    report = {
        "applied": False,
        "gate_passed": accepted,
        "standard_total_reviewed": len(gold_all),
        "standard_in_population": len(gold),
        "standard_excluded": sorted(gold_all.keys() - members),
        "standard_blank": sorted(c for c, v in gold.items() if not v),
        "standard": gold_all,
        "scores": scores,
        "scores_iy_insensitive": {
            s: score_iy_insensitive(data, gold) for s, data in strategies.items()
        },
        "unihan_without_overrides_diagnostic": raw_unihan,
        "mismatches": [
            {
                "char": c,
                "gold": v,
                "combined": strategies["combined"].get(c, []),
                "kanjidic2": kanjidic.get(c, []),
                "unihan": unihan.get(c, ([], None))[0],
            }
            for c, v in gold.items()
            if v and strategies["combined"].get(c, [])[:1] != v[:1]
        ],
        "population_before_filter": len(counts),
        "population_after_filter": len(eligible),
        "excluded_characters": excluded,
        "excluded_entry_weight": sum(counts[c] for c in excluded),
        "coverage_actual_before": coverage(current, eligible),
        "coverage_actual_after": coverage(current, eligible),
        "coverage_proposed_not_applied": coverage(strategies["combined_override"], eligible),
        "review4_created": False,
        "review4_count": None,
        "pending_unreviewed": ["繰", "扱"],
        "files_sha256": {
            p.as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in [*REVIEWS, READINGS, VARIANTS, OVERRIDES, KANJIDIC]
        },
    }
    Path("verification/m7b-evaluation.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    mismatch_lines = [
        "# M7b — Combined mismatches (gate failed)",
        "",
        "| Chữ | Chuẩn | Combined | KANJIDIC2 | Unihan |",
        "| --- | --- | --- | --- | --- |",
    ]
    for row in report["mismatches"]:
        mismatch_lines.append(
            "| "
            + " | ".join(
                [
                    row["char"],
                    *(
                        " / ".join(row[k]) or "—"
                        for k in ["gold", "combined", "kanjidic2", "unihan"]
                    ),
                ]
            )
            + " |"
        )
    Path("verification/m7b-combined-mismatches.md").write_text(
        "\n".join(mismatch_lines) + "\n", encoding="utf-8"
    )
    print(
        json.dumps(
            {
                k: v
                for k, v in report.items()
                if k not in {"standard", "mismatches", "files_sha256"}
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return report


if __name__ == "__main__":
    asyncio.run(evaluate())
