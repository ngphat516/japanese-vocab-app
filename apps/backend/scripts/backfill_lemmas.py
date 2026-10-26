"""Backfill derived lemma arrays only; run after backing up the target database.

Run: uv run python -m scripts.backfill_lemmas [--dry-run]
"""

import argparse
import asyncio

from sqlalchemy import select, update

from app.db.session import Session
from app.modules.textbooks.models import Entry
from app.nlp.tokenizer import entry_lemmas


async def backfill(sessions=Session, *, dry_run=False, batch_size=500):
    changed, scanned, last_id = 0, 0, 0
    while True:
        async with sessions() as db, db.begin():
            rows = (
                await db.execute(
                    select(Entry.id, Entry.content, Entry.lemmas)
                    .where(Entry.id > last_id)
                    .order_by(Entry.id)
                    .limit(batch_size)
                )
            ).all()
            if not rows:
                break
            values = await asyncio.to_thread(
                lambda rows=rows: [entry_lemmas(row.content) for row in rows]
            )
            for row, value in zip(rows, values, strict=True):
                if row.lemmas != value:
                    changed += 1
                    if not dry_run:
                        # Do not overwrite concurrent content edits with stale derived data.
                        result = await db.execute(
                            update(Entry)
                            .where(
                                Entry.id == row.id,
                                Entry.content == row.content,
                                Entry.lemmas == row.lemmas,
                            )
                            .values(lemmas=value)
                        )
                        if result.rowcount != 1:
                            raise RuntimeError(
                                f"Entry {row.id} changed concurrently; rerun backfill"
                            )
            scanned += len(rows)
            last_id = rows[-1].id
    return {"dry_run": dry_run, "scanned": scanned, "changed": changed, "batch_size": batch_size}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    print(asyncio.run(backfill(dry_run=args.dry_run)))


if __name__ == "__main__":
    main()
