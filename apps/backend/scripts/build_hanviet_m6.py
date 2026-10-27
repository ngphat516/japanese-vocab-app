"""Build reviewed readings and next frequency batch using M5's exact population."""

import asyncio
import csv
import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path

from sqlalchemy import select

from app.db.session import engine
from app.modules.dictionary.models import Kanji, Word
from app.modules.textbooks.models import Entry
from app.nlp.furigana import japanese_strings
from scripts.build_hanviet_unihan import HAN, apply_overrides, parse, parse_variants, with_variants


async def build():
    result = apply_overrides(
        with_variants(
            parse(Path("data/unihan/Unihan_Readings.txt")),
            parse_variants(Path("data/unihan/Unihan_Variants.txt")),
        ),
        Path("data/hanviet_overrides.csv"),
    )
    async with engine.connect() as db:
        rows = (
            await db.execute(
                select(Word.kanji, Entry.content, Entry.id)
                .join(Entry, Entry.word_id == Word.id)
                .order_by(Entry.id)
            )
        ).all()
        current = dict((await db.execute(select(Kanji.char, Kanji.hanviet))).all())
        headwords = (await db.scalars(select(Word.kanji).order_by(Word.id))).all()
    await engine.dispose()
    counts, examples = Counter(), defaultdict(list)
    population = {c for word, _, _ in rows for c in word if HAN.fullmatch(c)}
    for word, content, _ in rows:
        counts.update(set(HAN.findall(word + " " + " ".join(japanese_strings(content)))))
    for word in headwords:
        for char in set(word):
            if word not in examples[char] and len(examples[char]) < 2:
                examples[char].append(word)
    ordered = sorted(counts, key=lambda c: (-counts[c], ord(c)))
    missing_examples = {char for char in ordered[300:600] if not examples[char]}
    source_only = sorted(missing_examples)
    for _, content, entry_id in rows:
        for value in japanese_strings(content):
            for char in list(missing_examples):
                index = value.find(char)
                if index >= 0:
                    excerpt = value[max(0, index - 1) : index + 1]
                    examples[char] = [f"{excerpt} (câu nguồn, entry {entry_id}; không có headword)"]
                    missing_examples.remove(char)

    def metrics(data, chars):
        return {
            "characters": len(chars),
            "covered": sum(bool(data.get(c)) for c in chars),
            "entry_weight": sum(counts[c] for c in chars),
            "covered_entry_weight": sum(counts[c] for c in chars if data.get(c)),
        }

    readings = {c: values for c, (values, _) in result.items()}
    report = {
        "headwords_before": metrics(current, sorted(population)),
        "headwords_after": metrics(readings, sorted(population)),
        "all_frequency_after": metrics(readings, ordered),
        "top300_before": metrics(current, ordered[:300]),
        "top300_after": metrics(readings, ordered[:300]),
        "missing_top300": [c for c in ordered[:300] if not readings.get(c)],
        "review_source_only": source_only,
    }
    with Path("data/hanviet.csv").open("w", encoding="utf-8", newline="") as handle:  # noqa: ASYNC230
        writer = csv.writer(handle)
        writer.writerow(["kanji", "hanviet", "source"])
        writer.writerows((c, "|".join(v), s) for c, (v, s) in sorted(result.items()))
    lines = [
        "# M6 Hán Việt — REVIEW lô 2",
        "",
        "Chữ 301–600; cùng population và tie-break M5. Âm chưa duyệt có thể lẫn Nôm.",
        "",
        "| Chữ | Âm | Source | Số entry | Biến thể | Từ ví dụ |",
        "| --- | --- | --- | ---: | --- | --- |",
    ]
    for char in ordered[300:600]:
        values, source = result.get(char, ([], None))
        lines.append(
            f"| {char} | {' / '.join(values) or '—'} | {source or '—'} | {counts[char]} | {'**unihan_variant**' if (source or '').startswith('unihan_variant:') else ''} | {' / '.join(examples[char]) or '—'} |"
        )
    Path("verification/m6_hanviet_review_2.md").write_text(
        "\n".join(lines) + "\n", encoding="utf-8"
    )
    Path("verification/m6-hanviet.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    Path("data/hanviet.metadata.json").write_text(
        json.dumps(
            {
                "unicode_version": "17.0.0",
                "milestone": 6,
                "coverage": report,
                "files_sha256": {
                    name: hashlib.sha256(Path(name).read_bytes()).hexdigest()
                    for name in [
                        "data/unihan/Unihan_Readings.txt",
                        "data/unihan/Unihan_Variants.txt",
                        "data/hanviet_overrides.csv",
                    ]
                },
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    asyncio.run(build())
