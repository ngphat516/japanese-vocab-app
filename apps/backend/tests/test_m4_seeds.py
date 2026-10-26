import csv

import pytest
from sqlalchemy import func, select

from app.core.exceptions import AppError
from app.modules.auth.service import current_user
from app.modules.textbooks.models import Entry, Lesson, Textbook
from scripts.seed_jlpt_textbooks import seed


async def test_jlpt_admin_idempotent_source_only(authorized, db, tmp_path):
    client, _ = authorized
    user = await current_user(db, client.headers["authorization"][7:])
    with pytest.raises(AppError):
        await seed(db, user, tmp_path)
    user.role = "admin"
    for level in range(1, 6):
        with (tmp_path / f"vocab-n{level}.csv").open("w", encoding="utf-8", newline="") as handle:
            writer = csv.writer(handle)
            writer.writerow(["word", "reading", "meanings", "level"])
            for i in range(51):
                writer.writerow([f"検証{i}", "けんしょう", f"source meaning {i}", f"N{level}"])
    report = await seed(db, user, tmp_path)
    assert len(report) == 5
    await seed(db, user, tmp_path)
    assert await db.scalar(select(func.count()).select_from(Textbook)) == 5
    assert await db.scalar(select(func.count()).select_from(Lesson)) == 10
    assert await db.scalar(select(func.count()).select_from(Entry)) == 255
    books = (await db.scalars(select(Textbook))).all()
    assert all(b.visibility == "public" and "CC BY-SA 4.0" in b.license for b in books)
    contents = (await db.scalars(select(Entry.content))).all()
    assert all(list(c[0]) == ["type", "en"] or set(c[0]) == {"type", "en"} for c in contents)
