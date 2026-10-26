"""Export exactly the ten reviewed M3 words and reopen all three formats; rollback."""

import asyncio
import hashlib
import json
import logging
import os
import uuid
from pathlib import Path

import httpx
from sqlalchemy import func, insert, select
from sqlalchemy.dialects.postgresql import insert as upsert

from app.core.security import token
from app.db.session import Session, engine, get_db
from app.main import app
from app.modules.auth.models import User
from app.modules.notebook.models import Collection, CollectionWord, SavedWord
from app.modules.textbooks.models import Entry, Lesson, Textbook
from scripts.measure_m3_exports import verify


async def main():
    previous = json.loads(Path("verification/m3/resources.json").read_text(encoding="utf-8"))
    ids = [word["id"] for word in previous["sample_words"]]
    assert len(ids) == 10
    output = Path("verification/m4_exports")
    output.mkdir(parents=True, exist_ok=True)
    report = {"sample_words": previous["sample_words"], "files": {}}
    async with Session() as db:
        tx = await db.begin()
        owner = await db.scalar(
            select(Textbook.owner_id)
            .join(Lesson, Lesson.textbook_id == Textbook.id)
            .join(Entry, Entry.lesson_id == Lesson.id)
            .where(Entry.word_id.in_(ids))
            .order_by(Textbook.id)
            .limit(1)
        )
        user = await db.get(User, owner)
        before = await db.scalar(select(func.count()).select_from(SavedWord))
        try:
            await db.execute(
                upsert(SavedWord)
                .values([{"user_id": owner, "word_id": word_id} for word_id in ids])
                .on_conflict_do_nothing(constraint="uq_saved_user_word")
            )
            saved = (
                await db.scalars(
                    select(SavedWord).where(SavedWord.user_id == owner, SavedWord.word_id.in_(ids))
                )
            ).all()
            collection = Collection(user_id=owner, name="__m4_sample_" + uuid.uuid4().hex)
            db.add(collection)
            await db.flush()
            await db.execute(
                insert(CollectionWord),
                [{"collection_id": collection.id, "saved_word_id": row.id} for row in saved],
            )

            async def dependency():
                yield db

            app.dependency_overrides[get_db] = dependency
            async with httpx.AsyncClient(
                transport=httpx.ASGITransport(app=app),
                base_url="http://verify",
                headers={"Authorization": "Bearer " + token(user.id, "access")[0]},
            ) as client:
                for format, ext in [("anki", "apkg"), ("csv", "csv"), ("markdown", "zip")]:
                    response = await client.get(
                        "/api/v1/saved-words/export",
                        params={"format": format, "collection_id": collection.id},
                    )
                    response.raise_for_status()
                    verify(response.content, format, 10)
                    path = output / f"m4-sample-10.{ext}"
                    path.write_bytes(response.content)
                    report["files"][format] = {
                        "path": str(path),
                        "bytes": len(response.content),
                        "sha256": hashlib.sha256(response.content).hexdigest(),
                        "reopened_words": 10,
                    }
        finally:
            app.dependency_overrides.clear()
            await tx.rollback()
        after = await db.scalar(select(func.count()).select_from(SavedWord))
        assert before == after
        report["saved_rows_before_after"] = [before, after]
    await engine.dispose()
    (output / "verification.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (output / "README.md").write_text(
        "# M4 — 10 từ giống mẫu M3\n\nAPKG: mở bằng Anki; CSV UTF-8 BOM: Excel/Quizlet; ZIP: giải nén vào Obsidian.\nĐã mở lại SQLite/CSV/ZIP để kiểm tra đủ 10 từ, không media. Ruby HTML, CSV text thuần.\nOCR cần đối chiếu; không sửa nguồn. Các dòng notebook tạm đã rollback.\n",
        encoding="utf-8",
    )
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    os.environ["RATE_LIMIT_ENABLED"] = "false"
    # Settings are cached during app import; disable the limiter for this local probe.
    from app.core.config import get_settings

    get_settings().rate_limit_enabled = False
    logging.disable(logging.INFO)
    asyncio.run(main())
