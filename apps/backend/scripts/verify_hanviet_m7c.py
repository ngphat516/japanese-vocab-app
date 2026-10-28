"""Verify the seeded DB against the complete M7c projection and source hash."""

import asyncio
import csv
import hashlib
import json
from collections import Counter
from pathlib import Path

from sqlalchemy import select

from app.db.session import engine
from app.modules.dictionary.models import Kanji, Word
from app.modules.textbooks.models import Entry
from app.nlp.furigana import japanese_strings
from scripts.build_hanviet_m7 import KANJIDIC, OVERRIDES
from scripts.build_hanviet_unihan import HAN, apply_overrides
from scripts.hanviet_sources import coverage, score


async def verify():
    build = json.loads(Path("verification/m7c-build.json").read_text(encoding="utf-8"))
    members = {r["literal"] for r in json.loads(KANJIDIC.read_text(encoding="utf-8"))["characters"]}
    async with engine.connect() as db:
        kanji = {
            r.char: (r.hanviet, r.hanviet_source)
            for r in (
                await db.execute(select(Kanji.char, Kanji.hanviet, Kanji.hanviet_source))
            ).all()
        }
        rows = (
            await db.execute(
                select(Word.kanji, Entry.content).join(Entry, Entry.word_id == Word.id)
            )
        ).all()
        original = (
            await db.execute(select(Entry.id, Entry.content, Entry.search_text).order_by(Entry.id))
        ).all()
    await engine.dispose()
    protected = set(build["protected_kanji"])
    # CSV plus overrides must describe the whole actual DB, except audited edits.
    projected = apply_overrides({}, Path("data/hanviet.csv"))
    # apply_overrides labels rows override; read the actual source separately.
    with Path("data/hanviet.csv").open(encoding="utf-8", newline="") as handle:  # noqa: ASYNC230
        sources = {r["kanji"]: r["source"] or None for r in csv.DictReader(handle)}
    overrides = apply_overrides({}, OVERRIDES)
    for c, (values, _) in projected.items():
        expected = overrides.get(c, (values, sources[c])) if c in members else ([], None)
        if c in protected:
            old = build["baseline_kanji"][c]
            expected = (old["hanviet"], old["source"])
        assert kanji[c] == expected, f"Projection mismatch for {c}"
    assert all(
        not values for c, (values, _) in kanji.items() if c not in members and c not in protected
    )
    assert all(kanji[r["char"]] == (r["after"], r["after_source"]) for r in build["changes"])
    counts = Counter()
    for word, content in rows:
        counts.update(set(HAN.findall(word + " " + " ".join(japanese_strings(content)))))
    eligible = {c: n for c, n in counts.items() if c in members}
    actual = coverage({c: v for c, (v, _) in kanji.items()}, eligible)
    assert actual == build["after_projected"]
    digest = hashlib.sha256(
        json.dumps([list(r) for r in original], ensure_ascii=False, sort_keys=True).encode()
    ).hexdigest()
    assert (
        len(original) == build["original_entries"] and digest == build["content_search_text_sha256"]
    )
    original_gold = json.loads(
        Path("verification/m7b-evaluation.json").read_text(encoding="utf-8")
    )["standard"]
    gold = {c: v for c, v in original_gold.items() if c in members}
    locked = score({c: v for c, (v, _) in kanji.items()}, gold)
    assert locked["first_match"] == 598 and kanji["込"][0] == []
    review = Path("verification/m7c_hanviet_review_4.md").read_text(encoding="utf-8")
    lines = [line for line in review.splitlines() if line.startswith("| ")][2:]
    assert len(lines) == build["review4_count"]
    assert all(line.split("|")[1].strip() in members for line in lines)
    report = {
        "after": actual,
        "locked_standard": locked,
        "overrides": len(overrides),
        "review4_count": len(lines),
        "changes_verified": len(build["changes"]),
        "excluded_local_with_readings": sum(
            bool(kanji.get(c, ([], None))[0]) for c in build["excluded"]
        ),
        "content_search_text_sha256": digest,
        "entries": len(original),
    }
    Path("verification/m7c-db-final.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    changes_path = Path("verification/m7c-hanviet-changes.md")
    changes_path.write_text(
        changes_path.read_text(encoding="utf-8").replace(
            "(projection; verify against DB)", "(verified against seeded DB)"
        ),
        encoding="utf-8",
    )
    metadata_path = Path("data/hanviet.metadata.json")
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    metadata["coverage_actual"] = actual
    metadata_path.write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    asyncio.run(verify())
