"""Read-only M1/M2 lemma comparison and source hash; run around backfill."""

import argparse
import asyncio
import hashlib
import json
import re
from pathlib import Path

from sqlalchemy import select

from app.db.session import engine
from app.modules.textbooks.models import Entry
from app.nlp.furigana import strip_markup
from app.nlp.tokenizer import lemmas


async def snapshot(output):
    async with engine.connect() as db:
        rows = (
            await db.execute(select(Entry.id, Entry.content, Entry.search_text).order_by(Entry.id))
        ).all()
    await engine.dispose()
    digest = hashlib.sha256(
        json.dumps([list(r) for r in rows], ensure_ascii=False, sort_keys=True).encode()
    ).hexdigest()
    output.write_text(
        json.dumps({"entries": len(rows), "content_search_text_sha256": digest}, indent=2),
        encoding="utf-8",
    )


def sample():
    source = Path("verification/m1_nlp_sample.md").read_text(encoding="utf-8")
    lines = [
        "# Milestone 2 lemma sample — MANUAL",
        "",
        "Seed: 20261020. Same 30 sentences and order as M1; source unchanged.",
        "",
    ]
    for section in source.split("## ")[1:]:
        title, body = section.split("\n", 1)
        original = re.search(r"Original:\s*\n\n(.*?)\n\nadd_furigana", body, re.DOTALL)[1]
        old = json.loads(body.split("Lemmas:")[1].strip())
        new = lemmas(strip_markup(original).replace("__", ""))
        lines += [
            "## " + title,
            "",
            original,
            "",
            "| Lemma M1 | Lemma M2 |",
            "| --- | --- |",
            "| "
            + json.dumps(old, ensure_ascii=False)
            + " | "
            + json.dumps(new, ensure_ascii=False)
            + " |",
            "",
        ]
    Path("verification/m2_lemma_sample.md").write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--snapshot", type=Path)
    args = parser.parse_args()
    if args.snapshot:
        asyncio.run(snapshot(args.snapshot))
    else:
        sample()
