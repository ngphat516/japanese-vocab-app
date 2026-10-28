"""Build combined fallback with locked reviews; all outputs are local projections."""

import asyncio
import csv
import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path

from sqlalchemy import select

from app.db.session import engine
from app.modules.dictionary.models import Kanji, KanjiEdit, Word
from app.modules.textbooks.models import Entry
from app.nlp.furigana import japanese_strings
from app.nlp.hanviet import combined_readings
from scripts.build_hanviet_m7 import KANJIDIC, OVERRIDES, READINGS, RELEASE, VARIANTS
from scripts.build_hanviet_unihan import HAN, apply_overrides, parse, parse_variants, with_variants
from scripts.evaluate_hanviet_m7b import REVIEWS, reviewed_standard
from scripts.hanviet_sources import coverage, parse_kanjidic2, score, score_iy_insensitive


def review_required(char, values, source, kanjidic):
    return (
        char in {"繰", "扱"}
        or not values
        or (source == "kanjidic2" and len(kanjidic) >= 2)
        or (source == "kanjidic2_unihan" and values[:1] != kanjidic[:1])
    )


async def build():
    document = json.loads(KANJIDIC.read_text(encoding="utf-8-sig"))
    if document["version"] != "3.6.2" or document["dictDate"] != "2026-10-19":
        raise ValueError("KANJIDIC2 does not match pinned M7 release")
    members = {row["literal"] for row in document["characters"]}
    kanjidic = parse_kanjidic2(KANJIDIC)
    unihan = with_variants(parse(READINGS), parse_variants(VARIANTS))
    combined = combined_readings(members, kanjidic, unihan)
    result = apply_overrides(combined, OVERRIDES)
    standard = reviewed_standard(REVIEWS, apply_overrides({}, OVERRIDES))
    # Require the original M7b gold snapshot as an independent comparison: do
    # not silently redefine gold from today's overrides to make a check pass.
    original_gold = json.loads(
        Path("verification/m7b-evaluation.json").read_text(encoding="utf-8")
    )["standard"]
    gold = {c: v for c, v in original_gold.items() if c in members}
    if any(standard[c] != v for c, v in gold.items()):
        raise ValueError("A reviewed reading changed relative to M7b gold")
    async with engine.connect() as db:
        rows = (
            await db.execute(
                select(Word.kanji, Entry.content).join(Entry, Entry.word_id == Word.id)
            )
        ).all()
        existing = {
            row.char: (row.hanviet, row.hanviet_source)
            for row in (
                await db.execute(select(Kanji.char, Kanji.hanviet, Kanji.hanviet_source))
            ).all()
        }
        edited = set((await db.scalars(select(KanjiEdit.char).distinct())).all())
        headwords = (await db.scalars(select(Word.kanji).order_by(Word.id))).all()
        source_rows = (
            await db.execute(select(Entry.id, Entry.content, Entry.search_text).order_by(Entry.id))
        ).all()
    await engine.dispose()
    content_hash = hashlib.sha256(
        json.dumps([list(r) for r in source_rows], ensure_ascii=False, sort_keys=True).encode()
    ).hexdigest()
    counts, examples = Counter(), defaultdict(list)
    for word, content in rows:
        counts.update(set(HAN.findall(word + " " + " ".join(japanese_strings(content)))))
    for word in headwords:
        for c in set(HAN.findall(word)):
            if word not in examples[c] and len(examples[c]) < 2:
                examples[c].append(word)
    eligible = {c: n for c, n in counts.items() if c in members}
    ordered = sorted(eligible, key=lambda c: (-counts[c], ord(c)))
    # Explicit rows clear old readings outside KANJIDIC2, including entries
    # that no longer occur in local text. Audit-edited Kanji remain protected.
    for c in existing.keys() | members | result.keys():
        if c not in members:
            result[c] = ([], None)
        else:
            result.setdefault(c, ([], None))
    projected = dict(result)
    projected.update({c: existing[c] for c in edited})
    strategies = {
        "unihan_raw": {c: v for c, (v, _) in unihan.items()},
        "kanjidic2": kanjidic,
        "combined": {c: v for c, (v, _) in combined.items()},
        "combined_override": {c: v for c, (v, _) in result.items()},
    }
    scores = {s: score(data, gold) for s, data in strategies.items()}
    if scores["combined_override"]["first_match"] != 598:
        raise ValueError("Locked standard must match all 598 nonempty reviewed readings")
    changes = [
        {
            "char": c,
            "before": old,
            "before_source": source,
            "after": projected[c][0],
            "after_source": projected[c][1],
            "entries": counts[c],
        }
        for c, (old, source) in existing.items()
        if old and old != projected[c][0]
    ]
    changes.sort(key=lambda r: (-r["entries"], ord(r["char"])))
    selected = [
        c
        for rank, c in enumerate(ordered, 1)
        if (rank >= 1201 or c in {"繰", "扱"})
        and review_required(c, *projected[c], kanjidic.get(c, []))
    ]
    rank_by_char = {c: n for n, c in enumerate(ordered, 1)}
    report = {
        "milestone": "7c",
        "decision": "user-authorized fallback; M7b gate superseded",
        "scores": scores,
        "scores_iy_insensitive": {
            s: score_iy_insensitive(data, gold) for s, data in strategies.items()
        },
        "before": coverage({c: v for c, (v, _) in existing.items()}, eligible),
        "after_projected": coverage({c: v for c, (v, _) in projected.items()}, eligible),
        "excluded": sorted(counts.keys() - members),
        "changes": changes,
        "changes_local": sum(r["entries"] > 0 for r in changes),
        "review4_count": len(selected),
        "review4_characters": selected,
        "forced_pending_ranks": {c: rank_by_char.get(c) for c in ["繰", "扱"]},
        "protected_kanji": sorted(edited),
        "original_entries": len(source_rows),
        "content_search_text_sha256": content_hash,
        "baseline_kanji": {c: {"hanviet": v, "source": s} for c, (v, s) in existing.items()},
    }
    with Path("data/hanviet.csv").open("w", encoding="utf-8", newline="") as handle:  # noqa: ASYNC230
        writer = csv.writer(handle)
        writer.writerow(["kanji", "hanviet", "source"])
        writer.writerows((c, "|".join(v), s) for c, (v, s) in sorted(result.items()))
    review = [
        "# M7c — Hán Việt REVIEW lô 4",
        "",
        "Hạng1201+ trong population KANJIDIC2; cộng 繰/扱 chưa duyệt dù ở hạng trước.",
        "Sort số entry giảm dần, tie-break code point. Chỉ headword thật; không có ghi rõ.",
        "",
        "| Chữ | Âm được chọn | Source | Âm KANJIDIC2 | Âm Unihan | Số entry | Từ ví dụ |",
        "| --- | --- | --- | --- | --- | ---: | --- |",
    ]
    for c in selected:
        values, source = projected[c]
        review.append(
            "| "
            + " | ".join(
                [
                    c,
                    " / ".join(values) or "—",
                    source or "—",
                    " / ".join(kanjidic.get(c, [])) or "—",
                    " / ".join(unihan.get(c, ([], None))[0]) or "—",
                    str(counts[c]),
                    " / ".join(examples[c]) or "không có headword",
                ]
            )
            + " |"
        )
    Path("verification/m7c_hanviet_review_4.md").write_text(
        "\n".join(review) + "\n", encoding="utf-8"
    )
    lines = [
        "# M7c — Readings changed after seed (projection; verify against DB)",
        "",
        "All DB characters with a nonempty old reading; sorted entry count descending/code point.",
        "",
        "| Chữ | Trước | Source trước | Sau | Source sau | Số entry |",
        "| --- | --- | --- | --- | --- | ---: |",
    ]
    for r in changes:
        lines.append(
            f"| {r['char']} | {' / '.join(r['before'])} | {r['before_source'] or '—'} | {' / '.join(r['after']) or '—'} | {r['after_source'] or '—'} | {r['entries']} |"
        )
    Path("verification/m7c-hanviet-changes.md").write_text(
        "\n".join(lines) + "\n", encoding="utf-8"
    )
    Path("verification/m7c-build.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    metadata = {
        "milestone": "7c",
        "unicode_version": "17.0.0",
        "priority": ["override", "combined", "unihan", "unihan_variant"],
        "population": "KANJIDIC2 membership; clear excluded automatic readings",
        "kanjidic2": {
            "release": RELEASE,
            "version": document["version"],
            "dictDate": document["dictDate"],
            "license": "CC-BY-SA-4.0",
            "source": "https://github.com/scriptin/jmdict-simplified/releases/tag/3.6.2%2B20261019180022",
            "attribution": "EDRDG; vietnam readings Minh Chau Pham; JSON scriptin",
        },
        "scores": scores,
        "scores_iy_insensitive": report["scores_iy_insensitive"],
        "coverage_projected": report["after_projected"],
        "files_sha256": {
            p.as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in [
                KANJIDIC,
                READINGS,
                VARIANTS,
                OVERRIDES,
                *REVIEWS,
                Path("verification/m7b-evaluation.json"),
            ]
        },
    }
    Path("data/hanviet.metadata.json").write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(
        json.dumps(
            {
                k: v
                for k, v in report.items()
                if k not in {"changes", "baseline_kanji", "review4_characters", "excluded"}
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    print(f"Changes: {len(changes)}; local: {report['changes_local']}")


if __name__ == "__main__":
    asyncio.run(build())
