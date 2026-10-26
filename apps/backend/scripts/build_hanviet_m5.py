"""Offline variants/approved overrides and frequency review; never seed automatically."""

import argparse
import asyncio
import csv
import hashlib
import json
from collections import Counter
from pathlib import Path

from sqlalchemy import select

from app.db.session import engine
from app.modules.dictionary.models import Word
from app.modules.textbooks.models import Entry
from app.nlp.furigana import japanese_strings
from scripts.build_hanviet_unihan import HAN, apply_overrides, parse, parse_variants, with_variants


async def build(args):
    direct = parse(args.readings)
    variants = with_variants(direct, parse_variants(args.variants))
    result = apply_overrides(variants, args.overrides)
    async with engine.connect() as db:
        rows = (
            await db.execute(
                select(Word.kanji, Entry.content).join(Entry, Entry.word_id == Word.id)
            )
        ).all()
    await engine.dispose()
    population = {c for word, _ in rows for c in word if HAN.fullmatch(c)}
    counts = Counter()
    for word, content in rows:
        counts.update(set(HAN.findall(word + " " + " ".join(japanese_strings(content)))))
    coverage = {
        label: sum(bool(data.get(c, ([], None))[0]) for c in population)
        for label, data in [
            ("direct", {c: (v, "unihan") for c, v in direct.items()}),
            ("variants", variants),
            ("overrides", result),
        ]
    }
    with args.output.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["kanji", "hanviet", "source"])
        writer.writerows(
            (c, "|".join(values), source) for c, (values, source) in sorted(result.items())
        )
    report = {
        "unicode_version": "17.0.0",
        "files_sha256": {
            str(p): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in [args.readings, args.variants, args.overrides]
        },
        "local_characters": len(population),
        "covered": coverage,
        "coverage_percent": {k: 100 * v / len(population) for k, v in coverage.items()},
        "review_population": "headword + Japanese example/usage/collocation; distinct character per entry",
        "review_rows": min(300, len(counts)),
    }
    lines = [
        "# M5 Hán Việt — REVIEW",
        "",
        "300 chữ theo số entry giảm dần, tie-break Unicode. kVietnamese có thể lẫn âm Nôm; sửa dần qua PATCH /kanji.",
        "",
        "| Chữ | Âm | Source | Số entry | Biến thể |",
        "| --- | --- | --- | ---: | --- |",
    ]
    for char, count in sorted(counts.items(), key=lambda item: (-item[1], ord(item[0])))[:300]:
        values, source = result.get(char, ([], None))
        lines.append(
            f"| {char} | {' / '.join(values) or '—'} | {source or '—'} | {count} | {'**unihan_variant**' if (source or '').startswith('unihan_variant:') else ''} |"
        )
    args.review.write_text("\n".join(lines) + "\n", encoding="utf-8")
    args.output.with_suffix(".metadata.json").write_text(
        json.dumps(report, indent=2), encoding="utf-8"
    )
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--readings", type=Path, default=Path("data/unihan/Unihan_Readings.txt"))
    parser.add_argument("--variants", type=Path, default=Path("data/unihan/Unihan_Variants.txt"))
    parser.add_argument("--overrides", type=Path, default=Path("data/hanviet_overrides.csv"))
    parser.add_argument("--output", type=Path, default=Path("data/hanviet.csv"))
    parser.add_argument("--review", type=Path, default=Path("verification/m5_hanviet_review.md"))
    asyncio.run(build(parser.parse_args()))
