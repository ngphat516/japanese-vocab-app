"""Durable import phases. Queue locks plus row claims prevent duplicate execution."""

import asyncio
import io
from datetime import UTC, datetime, timedelta

from pydantic import ValidationError
from sqlalchemy import delete, select
from sqlalchemy.exc import DBAPIError, InterfaceError, OperationalError

from app.core.exceptions import AppError
from app.db.session import Session
from app.modules.auth.models import User
from app.modules.imports import service
from app.modules.imports.models import ImportJob, ImportRow


class TransientImportError(Exception):
    """Only transient database failures are retried by Procrastinate."""


async def recover_stalled(sessions=Session):
    async with sessions() as db, db.begin():
        rows = (
            await db.scalars(
                select(ImportJob)
                .where(
                    ImportJob.status.in_(["processing", "committing"]),
                    ImportJob.updated_at < datetime.now(UTC) - timedelta(minutes=15),
                )
                .with_for_update(skip_locked=True)
            )
        ).all()
        for job in rows:
            job.status, job.error, job.failed, job.payload = "failed", "WORKER_TIMEOUT", 1, None
            await db.execute(delete(ImportRow).where(ImportRow.job_id == job.id))
        return len(rows)


def is_transient(exc):
    if isinstance(exc, (ConnectionError, TimeoutError, OSError, OperationalError, InterfaceError)):
        return True
    return isinstance(exc, DBAPIError) and (
        exc.connection_invalidated
        or getattr(exc.orig, "sqlstate", "") in {"40001", "40P01", "57P01", "57P02", "57P03"}
    )


async def fail_or_retry(sessions, job_id, phase, exc, attempt):
    async with sessions() as db, db.begin():
        job = await db.scalar(select(ImportJob).where(ImportJob.id == job_id).with_for_update())
        if not job or job.status in {"done", "review", "failed"}:
            return False
        if is_transient(exc) and attempt < 3:
            job.status = "pending" if phase == "parse" else "commit_pending"
            job.error = "TRANSIENT_DATABASE_ERROR"
            return True
        job.status, job.failed, job.payload = "failed", 1, None
        job.error = (
            exc.code
            if isinstance(exc, AppError)
            else "IMPORT_INVALID_ROW"
            if isinstance(exc, (ValueError, TypeError, KeyError, ValidationError))
            else "DATABASE_RETRY_EXHAUSTED"
            if is_transient(exc)
            else "IMPORT_WORKER_FAILED"
        )
        await db.execute(delete(ImportRow).where(ImportRow.job_id == job_id))
    return False


async def run_job(job_id, phase, *, sessions=Session, attempt=0):
    expected = "pending" if phase == "parse" else "commit_pending"
    try:
        async with sessions() as db, db.begin():
            job = await db.scalar(select(ImportJob).where(ImportJob.id == job_id).with_for_update())
            active = "processing" if phase == "parse" else "committing"
            if job and job.status == active and attempt > 0:
                # Queue lock excludes another runner, including when recording a
                # transient failure also lost its connection. Never replay stale work.
                if job.updated_at < datetime.now(UTC) - timedelta(minutes=15):
                    job.status, job.error, job.failed, job.payload = (
                        "failed",
                        "WORKER_TIMEOUT",
                        1,
                        None,
                    )
                    await db.execute(delete(ImportRow).where(ImportRow.job_id == job_id))
                    return
            elif not job or job.status != expected:
                return
            user = await db.get(User, job.user_id)
            await service.get_job(db, user, job.id)
            job.status, job.error, job.processed = (
                ("processing" if phase == "parse" else "committing"),
                None,
                0,
            )
            payload, adapter, filename = job.payload, job.adapter, job.file_key
            if phase == "parse":
                await db.execute(delete(ImportRow).where(ImportRow.job_id == job_id))
                job.total = job.matched = job.ambiguous = 0
        if phase == "parse":
            source = io.BytesIO(payload or b"")
            source.name = filename
            rows = await asyncio.to_thread(service.ADAPTERS[adapter].parse, source)
            async with sessions() as db, db.begin():
                job = await db.get(ImportJob, job_id)
                job.total = len(rows)
            for start in range(0, len(rows), 100):
                async with sessions() as db, db.begin():
                    job = await db.scalar(
                        select(ImportJob).where(ImportJob.id == job_id).with_for_update()
                    )
                    if job.status != "processing":
                        return
                    user = await db.get(User, job.user_id)
                    await service.get_job(db, user, job_id)
                    await service.stage_rows(db, user, job, rows[start : start + 100], start)
            async with sessions() as db, db.begin():
                job = await db.scalar(
                    select(ImportJob).where(ImportJob.id == job_id).with_for_update()
                )
                if job.status == "processing":
                    job.status, job.payload = "review", None
        else:
            async with sessions() as db, db.begin():
                job = await db.get(ImportJob, job_id)
                user = await db.get(User, job.user_id)
                await service.commit(db, user, job_id, job.auto_furigana, worker=True)
    except Exception as exc:
        try:
            retry = await fail_or_retry(sessions, job_id, phase, exc, attempt)
        except Exception as persistence_error:
            if is_transient(persistence_error):
                raise TransientImportError(
                    "Database unavailable while recording import state"
                ) from persistence_error
            raise
        if retry:
            raise TransientImportError(
                "Transient database failure; transaction rolled back"
            ) from exc


def register(app, sessions=Session):
    import procrastinate

    @app.task(
        name="vocab.import",
        queue="imports",
        pass_context=True,
        retry=procrastinate.RetryStrategy(
            max_attempts=3, exponential_wait=2, retry_exceptions=(TransientImportError,)
        ),
    )
    async def import_task(context, job_id, phase):
        await run_job(job_id, phase, sessions=sessions, attempt=context.job.attempts)

    return import_task
