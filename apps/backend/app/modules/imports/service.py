import asyncio
import io
import json
from pathlib import Path

from pydantic import ValidationError
from sqlalchemy import func, select, text
from sqlalchemy.exc import IntegrityError

from app.core.config import get_settings
from app.core.exceptions import AppError
from app.modules.dictionary import service as dictionary
from app.modules.textbooks import service as textbooks
from app.modules.textbooks.blocks import validate_content

from .adapters.csv_template import COLUMNS, CSVTemplateAdapter
from .adapters.free_text import FreeTextAdapter, validate_text
from .adapters.mimikara import MimikaraAdapter
from .adapters.normalized_json import NormalizedJSONAdapter
from .models import ImportJob, ImportRow

ADAPTERS = {
    "free_text": FreeTextAdapter(),
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


def parse_payload(adapter, filename, payload):
    options = {}
    if adapter == "free_text":
        options = json.loads(payload)
        payload = options.pop("text").encode("utf-8")
    source = io.BytesIO(payload)
    source.name = filename
    return ADAPTERS[adapter].parse(source, **options)


async def upload(db, user, textbook_id, adapter, filename, payload, *, options=None):
    book = await textbooks.get_textbook(db, user, textbook_id, True)
    if adapter not in ADAPTERS:
        raise AppError(422, "UNKNOWN_ADAPTER", "Adapter không được hỗ trợ")
    if adapter == "free_text":
        if Path(filename).suffix.lower() != ".txt":
            raise AppError(422, "IMPORT_FORMAT", "free_text chỉ hỗ trợ TXT UTF-8")
        value = validate_text(payload)
        payload = json.dumps(
            {
                "text": value,
                "lesson_no": 1,
                "include_proper_nouns": False,
                "exclude_jlpt": [],
                **(options or {}),
            },
            ensure_ascii=False,
        ).encode()
    if adapter == "mimikara" and book.visibility != "private":
        raise AppError(422, "PRIVATE_REQUIRED", "Mimikara phải được import vào giáo trình private")
    if len(payload) > 5 * 1024 * 1024:
        raise AppError(413, "IMPORT_FILE_TOO_LARGE", "File vượt quá 5 MB")
    if get_settings().import_mode == "async":
        job = ImportJob(
            user_id=user.id,
            textbook_id=textbook_id,
            adapter=adapter,
            file_key=Path(filename).name,
            payload=payload,
            status="pending",
        )
        db.add(job)
        await db.flush()
        await enqueue(db, job.id, "parse")
        return job
    try:
        rows = await asyncio.to_thread(parse_payload, adapter, filename, payload)
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
        await stage_rows(db, user, job, rows)
        job.status = "review"
        await db.flush()
    return job


async def stage_rows(db, user, job, rows, start=0):
    lessons = {}
    matches = await dictionary.match_many(db, [(row.kanji, row.kana) for row in rows])
    for number, (row, candidates) in enumerate(zip(rows, matches, strict=True), start + 1):
        if row.lesson_no not in lessons:
            lessons[row.lesson_no] = await textbooks.ensure_lesson(
                db, user, job.textbook_id, row.lesson_no
            )
        status = "auto" if len(candidates) == 1 else "ambiguous" if candidates else "none"
        excluded = row.raw.get("exclude_jlpt", []) if job.adapter == "free_text" else []
        if candidates and all(w.jlpt_level in excluded for w in candidates):
            status = "skipped"
            row.raw["skip_reason"] = "EXCLUDED_JLPT"
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
        job.processed = number
    await db.flush()


def job_output(job):
    fields = [
        "id",
        "user_id",
        "textbook_id",
        "adapter",
        "file_key",
        "status",
        "total",
        "matched",
        "ambiguous",
        "failed",
        "error",
        "created_at",
        "updated_at",
    ]
    return {
        **{name: getattr(job, name) for name in fields},
        "progress": {"processed": job.processed, "total": job.total},
    }


async def enqueue(db, job_id, phase):
    import json

    await db.execute(text("SELECT set_config('search_path', 'procrastinate,public', true)"))
    return await db.scalar(
        text(
            "SELECT (procrastinate_defer_jobs_v1(ARRAY[ROW('imports', 'vocab.import', 0, :lock, :lock, CAST(:args AS jsonb), NULL)::procrastinate_job_to_defer_v1]))[1]"
        ),
        {"lock": f"import:{job_id}", "args": json.dumps({"job_id": job_id, "phase": phase})},
    )


async def request_commit(db, user, job_id, auto_furigana):
    job = await get_job(db, user, job_id, True)
    if job.status != "review":
        raise AppError(409, "IMPORT_STATE", "Job không ở bước review")
    if await db.scalar(
        select(ImportRow.id)
        .where(ImportRow.job_id == job_id, ImportRow.match_status == "ambiguous")
        .limit(1)
    ):
        raise AppError(409, "REVIEW_REQUIRED", "Còn dòng cần xác nhận")
    job.status, job.auto_furigana, job.processed = "commit_pending", auto_furigana, 0
    await enqueue(db, job_id, "commit")
    await db.flush()
    return job_output(job)


async def get_job(db, user, job_id, lock=False):
    stmt = select(ImportJob).where(ImportJob.id == job_id, ImportJob.user_id == user.id)
    if lock:
        stmt = stmt.with_for_update()
    job = await db.scalar(stmt.execution_options(populate_existing=True))
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


async def commit(db, user, job_id, auto_furigana=True, *, worker=False):
    job = await get_job(db, user, job_id, True)
    book = await textbooks.get_textbook(db, user, job.textbook_id, True)
    if job.status != ("committing" if worker else "review"):
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
            prepared = []
            lesson_cache = {}
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
                if row.lesson_no not in lesson_cache:
                    lesson_cache[row.lesson_no] = await textbooks.ensure_lesson(
                        db, user, book.id, row.lesson_no
                    )
                lesson = lesson_cache[row.lesson_no]
                prepared.append((lesson.id, word_id, row.order_no, blocks))
            word_cache = await dictionary.all_by_ids(db, {item[1] for item in prepared})
            readings = (
                await textbooks.textbook_readings(
                    db, job.textbook_id, [word.id for word in word_cache]
                )
                if auto_furigana
                else {}
            )
            for lesson_id, word_id, order_no, blocks in prepared:
                await textbooks.save_entry(
                    db,
                    user,
                    lesson_id,
                    word_id,
                    order_no,
                    blocks,
                    auto_furigana=auto_furigana,
                    readings=readings,
                )
            job.status = "done"
            job.processed = job.total
            job.payload = None
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
