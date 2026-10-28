"""Evaluate pinned KANJIDIC2, build reviewed readings, and generate local review 3."""

import asyncio
import csv
import hashlib
import json
import re
from collections import Counter, defaultdict
from pathlib import Path

from sqlalchemy import select

from app.db.session import engine
from app.modules.dictionary.models import Kanji, KanjiEdit, Word
from app.modules.textbooks.models import Entry
from app.nlp.furigana import japanese_strings
from scripts.build_hanviet_unihan import HAN, apply_overrides, parse, parse_variants, with_variants
from scripts.hanviet_sources import (
    combine,
    coverage,
    needs_review,
    parse_kanjidic2,
    prefer_kanjidic2,
    score,
)

RELEASE = "3.6.2+20261019180022"
KANJIDIC = Path("data/kanjidic2/kanjidic2-en-3.6.2.json")
READINGS = Path("data/unihan/Unihan_Readings.txt")
VARIANTS = Path("data/unihan/Unihan_Variants.txt")
OVERRIDES = Path("data/hanviet_overrides.csv")


def legacy_variants(path):
    """Reproduce M6 only to list every reading affected by removing semantic edges."""
    graph = {}
    for line in path.read_text(encoding="utf-8-sig").splitlines():
        if not line or line.startswith("#"):
            continue
        code, field, value = line.split("\t", 2)
        if field in {
            "kTraditionalVariant",
            "kZVariant",
            "kSemanticVariant",
            "kSpecializedSemanticVariant",
        }:
            graph.setdefault(chr(int(code.removeprefix("U+"), 16)), set()).update(
                chr(int(v, 16)) for v in re.findall(r"U\+([0-9A-Fa-f]+)", value)
            )
    return graph


async def build():
    header = json.loads(KANJIDIC.read_text(encoding="utf-8-sig"))
    if header["version"] != "3.6.2" or header["dictDate"] != "2026-10-19":
        raise ValueError("KANJIDIC2 does not match the pinned JMdict release")
    direct = parse(READINGS)
    variants = with_variants(direct, parse_variants(VARIANTS))
    old_variants = with_variants(direct, legacy_variants(VARIANTS))
    kanjidic = parse_kanjidic2(KANJIDIC)
    standard = {c: v for c, (v, _) in apply_overrides({}, OVERRIDES).items() if v}
    sources = {
        "kanjidic2": kanjidic,
        "unihan": direct,
        # Variant fallback is measured separately, not credited with direct readings.
        "unihan_variant": {
            c: v for c, (v, s) in variants.items() if s.startswith("unihan_variant:")
        },
    }
    scores = {s: score(data, standard) for s, data in sources.items()}
    prefer = prefer_kanjidic2(scores)
    result = combine(direct, variants, kanjidic, OVERRIDES, prefer)
    # Include explicit empty rows for removed legacy fallbacks. Omitting a row
    # would leave obsolete readings in the database on subsequent seeds.
    for c in old_variants.keys() - result.keys():
        result[c] = ([], None)
    async with engine.connect() as db:
        rows = (
            await db.execute(
                select(Word.kanji, Entry.content, Entry.id)
                .join(Entry, Entry.word_id == Word.id)
                .order_by(Entry.id)
            )
        ).all()
        current = dict((await db.execute(select(Kanji.char, Kanji.hanviet))).all())
        edited = set((await db.scalars(select(KanjiEdit.char).distinct())).all())
        headwords = (await db.scalars(select(Word.kanji).order_by(Word.id))).all()
    await engine.dispose()
    counts, examples = Counter(), defaultdict(list)
    population = {c for word, _, _ in rows for c in HAN.findall(word)}
    for word, content, _ in rows:
        counts.update(set(HAN.findall(word + " " + " ".join(japanese_strings(content)))))
    for word in headwords:
        for c in set(HAN.findall(word)):
            if word not in examples[c] and len(examples[c]) < 2:
                examples[c].append(word)
    ordered = sorted(counts, key=lambda c: (-counts[c], ord(c)))
    projected = {c: v for c, (v, _) in result.items()}
    # PATCH audit protections apply to the projected DB outcome as well.
    projected.update({c: current[c] for c in edited})
    changes = [
        {
            "char": c,
            "before": old_variants.get(c, ([], None))[0],
            "after": variants.get(c, ([], None))[0],
            "local_entries": counts[c],
        }
        for c in sorted(old_variants.keys() | variants.keys())
        if old_variants.get(c, ([], None))[0] != variants.get(c, ([], None))[0]
    ]
    selected = [
        c
        for c in ordered[600:1200]
        if needs_review(projected.get(c, []), kanjidic.get(c, []), variants.get(c, ([], None))[0])
    ]
    report = {
        "scores": scores,
        "prefer_kanjidic2": prefer,
        "priority": ["override", *(["kanjidic2"] if prefer else []), "unihan", "unihan_variant"],
        "source_coverage": {s: coverage(d, counts) for s, d in sources.items()},
        "all_before": coverage(current, counts),
        "all_after": coverage(projected, counts),
        "headwords_before": coverage(current, {c: counts[c] for c in population}),
        "headwords_after": coverage(projected, {c: counts[c] for c in population}),
        "strict_variant_changes": changes,
        "review3_count": len(selected),
        "review3_population": len(ordered[600:1200]),
        "protected_kanji": sorted(edited),
    }
    with Path("data/hanviet.csv").open("w", encoding="utf-8", newline="") as f:  # noqa: ASYNC230
        writer = csv.writer(f)
        writer.writerow(["kanji", "hanviet", "source"])
        writer.writerows((c, "|".join(v), s) for c, (v, s) in sorted(result.items()))
    lines = [
        "# M7 Hán Việt — REVIEW lô 3",
        "",
        "Hạng 601–1.200 theo population/tie-break M5. Chỉ thiếu âm, khác âm đầu, hoặc ≥3 âm.",
        "Loại chữ hai nguồn có cùng tập âm chuẩn hóa; nguồn thiếu không tính là đồng thuận. Không bịa headword.",
        "",
        "| Chữ | Âm đang dùng | Source | Âm KANJIDIC2 | Âm Unihan | Số entry | Từ ví dụ |",
        "| --- | --- | --- | --- | --- | ---: | --- |",
    ]
    for c in selected:
        values = [
            c,
            " / ".join(projected.get(c, [])) or "—",
            "override (PATCH)" if c in edited else result.get(c, ([], None))[1] or "—",
            " / ".join(kanjidic.get(c, [])) or "—",
            " / ".join(variants.get(c, ([], None))[0]) or "—",
            str(counts[c]),
            " / ".join(examples[c]) or "không có headword",
        ]
        lines.append("| " + " | ".join(values) + " |")
    Path("verification/m7_hanviet_review_3.md").write_text(
        "\n".join(lines) + "\n", encoding="utf-8"
    )
    Path("verification/m7-hanviet.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    Path("verification/m7-strict-variant-changes.md").write_text(
        "# M7 — Strict variant changes\n\nBefore/after without overrides or KANJIDIC2; all source characters.\n\n"
        "| Chữ | Trước | Sau | Số entry local |\n| --- | --- | --- | ---: |\n"
        + "\n".join(
            f"| {r['char']} | {' / '.join(r['before']) or '—'} | {' / '.join(r['after']) or '—'} | {r['local_entries']} |"
            for r in changes
        )
        + "\n",
        encoding="utf-8",
    )
    metadata = {
        "unicode_version": "17.0.0",
        "milestone": 7,
        "coverage": report,
        "kanjidic2": {
            "release": RELEASE,
            "version": "3.6.2",
            "dictDate": "2026-10-19",
            "source": "https://github.com/scriptin/jmdict-simplified/releases/tag/3.6.2%2B20261019180022",
            "license": "CC-BY-SA-4.0",
            "attribution": "KANJIDIC2 / EDRDG; vietnam readings: Minh Chau Pham",
        },
        "files_sha256": {
            str(p): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in [READINGS, VARIANTS, OVERRIDES, KANJIDIC]
        },
    }
    Path("data/hanviet.metadata.json").write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(
        json.dumps(
            {k: v for k, v in report.items() if k != "strict_variant_changes"},
            ensure_ascii=False,
            indent=2,
        )
    )
    print(f"Strict variant changes: {len(changes)} (full list in verification/m7-hanviet.json)")


if __name__ == "__main__":
    asyncio.run(build())
