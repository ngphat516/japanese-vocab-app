import asyncio
import io
from pathlib import Path

from pydantic import ValidationError
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError

from app.core.exceptions import AppError
from app.modules.dictionary import service as dictionary
from app.modules.textbooks import service as textbooks
from app.modules.textbooks.blocks import validate_content

from .adapters.csv_template import COLUMNS, CSVTemplateAdapter
from .adapters.mimikara import MimikaraAdapter
from .adapters.normalized_json import NormalizedJSONAdapter
from .models import ImportJob, ImportRow

ADAPTERS = {
    "csv_template": CSVTemplateAdapter(),
    "mimikara": MimikaraAdapter(),
    "normalized_json": NormalizedJSONAdapter(),
}


async def has_mimikara_import(db, textbook_id):
    return bool(
        await db.scalar(
            select(ImportJob.id)
            .where(ImportJob.textbook_id == textbook_id, ImportJob.adapter == "mimikara")
            .limit(1)
        )
    )


def adapters():
    return [
        {"name": name, "formats": getattr(adapter, "formats", ["csv", "xlsx"])}
        for name, adapter in ADAPTERS.items()
    ]


def template():
    return ",".join(COLUMNS) + "\n1,1,緊張,きんちょう,căng thẳng,tension,,,,\n"


async def upload(db, user, textbook_id, adapter, filename, payload):
    book = await textbooks.get_textbook(db, user, textbook_id, True)
    if adapter not in ADAPTERS:
        raise AppError(422, "UNKNOWN_ADAPTER", "Adapter không được hỗ trợ")
    if adapter == "mimikara" and book.visibility != "private":
        raise AppError(422, "PRIVATE_REQUIRED", "Mimikara phải được import vào giáo trình private")
    source = io.BytesIO(payload)
    source.name = filename
    try:
        rows = await asyncio.to_thread(ADAPTERS[adapter].parse, source)
    except (ValueError, ValidationError, TypeError, KeyError) as exc:
        raise AppError(
            422, "IMPORT_INVALID_ROW", "Dữ liệu import không hợp lệ", {"reason": str(exc)[:500]}
        ) from None
    async with db.begin_nested():
        job = ImportJob(
            user_id=user.id,
            textbook_id=textbook_id,
            adapter=adapter,
            file_key=Path(filename).name,
            status="processing",
            total=len(rows),
            matched=0,
            ambiguous=0,
            failed=0,
        )
        db.add(job)
        await db.flush()
        for number, row in enumerate(rows, 1):
            await textbooks.ensure_lesson(db, user, textbook_id, row.lesson_no)
            candidates = await dictionary.match(db, row.kanji, row.kana)
            status = "auto" if len(candidates) == 1 else "ambiguous" if candidates else "none"
            job.matched += status == "auto"
            job.ambiguous += status == "ambiguous"
            db.add(
                ImportRow(
                    job_id=job.id,
                    row_no=number,
                    raw=row.raw,
                    kanji=row.kanji,
                    kana=row.kana,
                    lesson_no=row.lesson_no,
                    order_no=row.order_no,
                    content=[x.model_dump(exclude_none=True) for x in row.content],
                    match_status=status,
                    candidate_word_ids=[w.id for w in candidates],
                    chosen_word_id=candidates[0].id if status == "auto" else None,
                )
            )
        job.status = "review"
        await db.flush()
    return job


async def get_job(db, user, job_id, lock=False):
    stmt = select(ImportJob).where(ImportJob.id == job_id, ImportJob.user_id == user.id)
    if lock:
        stmt = stmt.with_for_update()
    job = await db.scalar(stmt)
    if not job:
        raise AppError(404, "IMPORT_NOT_FOUND", "Không tìm thấy import")
    await textbooks.get_textbook(db, user, job.textbook_id, True)
    return job


async def list_rows(db, user, job_id, status, page, size):
    await get_job(db, user, job_id)
    stmt = select(ImportRow).where(ImportRow.job_id == job_id)
    if status:
        stmt = stmt.where(ImportRow.match_status == status)
    total = await db.scalar(select(func.count()).select_from(stmt.subquery()))
    rows = (
        await db.scalars(stmt.order_by(ImportRow.row_no).offset((page - 1) * size).limit(size))
    ).all()
    return {"items": rows, "total": total, "page": page, "size": size}


async def review(db, user, job_id, row_id, data):
    job = await get_job(db, user, job_id, True)
    if job.status != "review":
        raise AppError(409, "IMPORT_STATE", "Job không ở bước review")
    row = await db.scalar(
        select(ImportRow).where(ImportRow.job_id == job_id, ImportRow.id == row_id)
    )
    if not row:
        raise AppError(404, "ROW_NOT_FOUND", "Không tìm thấy dòng")
    if data.skipped:
        row.match_status, row.chosen_word_id = "skipped", None
    else:
        if data.chosen_word_id not in row.candidate_word_ids:
            raise AppError(422, "INVALID_CANDIDATE", "Từ không thuộc danh sách ứng viên")
        row.chosen_word_id, row.match_status = data.chosen_word_id, "auto"
    await db.flush()
    job.matched = await db.scalar(
        select(func.count())
        .select_from(ImportRow)
        .where(ImportRow.job_id == job_id, ImportRow.match_status == "auto")
    )
    job.ambiguous = await db.scalar(
        select(func.count())
        .select_from(ImportRow)
        .where(ImportRow.job_id == job_id, ImportRow.match_status == "ambiguous")
    )
    return row


async def commit(db, user, job_id):
    job = await get_job(db, user, job_id, True)
    if job.status != "review":
        raise AppError(409, "IMPORT_STATE", "Job không ở bước review")
    rows = (
        await db.scalars(
            select(ImportRow).where(ImportRow.job_id == job_id).order_by(ImportRow.row_no)
        )
    ).all()
    if any(row.match_status == "ambiguous" for row in rows):
        raise AppError(409, "REVIEW_REQUIRED", "Còn dòng cần xác nhận")
    try:
        async with db.begin_nested():
            job.status = "committing"
            for row in rows:
                if row.match_status == "skipped":
                    continue
                blocks = validate_content(row.content)
                word_id = row.chosen_word_id
                if word_id is None:
                    candidates = await dictionary.match(db, row.kanji, row.kana)
                    exact = [w for w in candidates if w.kanji == row.kanji and w.kana == row.kana]
                    word_id = (
                        exact[0].id
                        if exact
                        else (await dictionary.create_word(db, row.kanji, row.kana)).id
                    )
                lesson = await textbooks.ensure_lesson(db, user, job.textbook_id, row.lesson_no)
                await textbooks.save_entry(db, user, lesson.id, word_id, row.order_no, blocks)
            job.status = "done"
            await db.flush()
    except (AppError, IntegrityError, ValidationError) as exc:
        # Savepoint reverts entries AND newly created words. Keep failure status outside it.
        await db.refresh(job)
        job.status, job.failed, job.error = "failed", 1, type(exc).__name__
        await db.flush()
        return {
            "id": job_id,
            "status": "failed",
            "error": {
                "code": "IMPORT_COMMIT_FAILED",
                "message": "Import đã rollback toàn bộ",
                "details": {},
            },
        }
    return {"id": job.id, "status": job.status}
