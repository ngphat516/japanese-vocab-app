import asyncio
import os
import subprocess
import sys
import uuid
from datetime import UTC, datetime, timedelta

import httpx
import pytest
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.core.config import get_settings
from app.db.session import get_db
from app.jobs.import_job import recover_stalled, run_job
from app.main import app
from app.modules.imports.models import ImportJob, ImportRow
from app.modules.textbooks.models import Entry
from app.worker import configure_event_loop, create_app
from tests.conftest import auth


@pytest.fixture
async def worker_env(pg_url, monkeypatch):
    # A disposable database keeps committed API/worker transactions out of old fixtures.
    name = "m5_" + uuid.uuid4().hex
    root = create_async_engine(pg_url, isolation_level="AUTOCOMMIT")
    async with root.connect() as connection:
        await connection.execute(text(f'CREATE DATABASE "{name}"'))
    url = pg_url.rsplit("/", 1)[0] + "/" + name
    await asyncio.to_thread(
        subprocess.run,
        [sys.executable, "-m", "alembic", "upgrade", "head"],
        env={**os.environ, "DATABASE_URL": url},
        check=True,
        capture_output=True,
    )
    engine = create_async_engine(url)
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    monkeypatch.setattr(get_settings(), "import_mode", "async")

    async def dependency():
        async with sessions() as db, db.begin():
            yield db

    app.dependency_overrides[get_db] = dependency
    queue = create_app(url, sessions)
    try:
        async with (
            queue.open_async(),
            httpx.AsyncClient(
                transport=httpx.ASGITransport(app=app), base_url="http://test"
            ) as client,
        ):
            headers, _ = await auth(client)
            client.headers.update(headers)
            book = (await client.post("/api/v1/textbooks", json={"name": "Async import"})).json()
            yield client, book, sessions, queue
    finally:
        app.dependency_overrides.clear()
        await engine.dispose()
        async with root.connect() as connection:
            await connection.execute(text(f'DROP DATABASE "{name}" WITH (FORCE)'))
        await root.dispose()


async def drain(queue):
    await queue.run_worker_async(
        queues=["imports"], wait=False, install_signal_handlers=False, listen_notify=False
    )


async def upload(client, book, payload=None):
    if payload is None:
        # Use real kana, not romaji.
        payload = "lesson,order,kanji,kana,meaning_en\n1,1,猫,ねこ,cat\n".encode()
    return await client.post(
        "/api/v1/imports",
        data={"textbook_id": str(book["id"]), "adapter": "csv_template"},
        files={"file": ("source.csv", payload, "text/csv")},
    )


async def test_async_full_flow_two_workers_and_private_job(worker_env):
    client, book, sessions, queue = worker_env
    response = await upload(client, book)
    assert response.status_code == 202, response.text
    job = response.json()
    assert job["status"] == "pending" and "payload" not in job
    assert job["progress"] == {"processed": 0, "total": 0}
    await asyncio.gather(drain(queue), drain(queue))
    url = f"/api/v1/imports/{job['id']}"
    staged = (await client.get(url)).json()
    assert staged["status"] == "review" and staged["progress"] == {"processed": 1, "total": 1}
    assert staged["updated_at"] >= job["updated_at"]
    assert (await client.get(url + "/rows")).json()["total"] == 1
    response = await client.post(url + "/commit")
    assert response.status_code == 202 and response.json()["status"] == "commit_pending"
    assert (await client.post(url + "/commit")).status_code == 409
    await asyncio.gather(drain(queue), drain(queue))
    assert (await client.get(url)).json()["status"] == "done"
    async with sessions() as db:
        assert await db.scalar(select(func.count()).select_from(Entry)) == 1
        assert await db.scalar(select(func.count()).select_from(ImportRow)) == 1
        assert (
            await db.scalar(
                text(
                    "SELECT count(*) FROM procrastinate.procrastinate_jobs WHERE status='succeeded'"
                )
            )
            == 2
        )
    headers, _ = await auth(client, "worker-other@example.com")
    client.headers.update(headers)
    for method, suffix in [("get", ""), ("get", "/rows"), ("post", "/commit")]:
        assert (await getattr(client, method)(url + suffix)).status_code == 404


async def test_async_parse_invalid_no_staging_no_retry(worker_env):
    client, book, sessions, queue = worker_env
    result = await upload(client, book, b"bad csv")
    assert result.status_code == 202
    await drain(queue)
    job = (await client.get(f"/api/v1/imports/{result.json()['id']}")).json()
    assert job["status"] == "failed" and job["error"]
    async with sessions() as db:
        assert await db.scalar(select(func.count()).select_from(ImportRow)) == 0
        assert await db.scalar(select(func.count()).select_from(Entry)) == 0
        assert (
            await db.scalar(text("SELECT max(attempts) FROM procrastinate.procrastinate_jobs")) == 1
        )


async def test_async_commit_rollback_and_stale_timeout(worker_env):
    client, book, sessions, queue = worker_env
    job_id = (await upload(client, book)).json()["id"]
    await drain(queue)
    async with sessions() as db, db.begin():
        row = await db.scalar(select(ImportRow).where(ImportRow.job_id == job_id))
        row.content = [{"type": "example"}]
    assert (await client.post(f"/api/v1/imports/{job_id}/commit")).status_code == 202
    await drain(queue)
    assert (await client.get(f"/api/v1/imports/{job_id}")).json()["status"] == "failed"
    async with sessions() as db, db.begin():
        assert await db.scalar(select(func.count()).select_from(Entry)) == 0
        job = await db.get(ImportJob, job_id)
        job.status = "committing"
        job.updated_at = datetime.now(UTC) - timedelta(minutes=16)
    assert await recover_stalled(sessions) == 1
    result = (await client.get(f"/api/v1/imports/{job_id}")).json()
    assert result["error"] == "WORKER_TIMEOUT"
    await run_job(job_id, "commit", sessions=sessions)
    assert (await client.get(f"/api/v1/imports/{job_id}")).json()["error"] == "WORKER_TIMEOUT"
    async with sessions() as db, db.begin():
        stale = await db.get(ImportJob, job_id)
        stale.status = "committing"
        stale.updated_at = datetime.now(UTC) - timedelta(minutes=16)
    await run_job(job_id, "commit", sessions=sessions, attempt=1)
    assert (await client.get(f"/api/v1/imports/{job_id}")).json()["error"] == "WORKER_TIMEOUT"


def test_windows_selector_policy(monkeypatch):
    from app import worker

    sentinel = object()
    calls = []
    monkeypatch.setattr(worker.sys, "platform", "win32")
    monkeypatch.setattr(
        worker.asyncio, "WindowsSelectorEventLoopPolicy", lambda: sentinel, raising=False
    )
    monkeypatch.setattr(worker.asyncio, "set_event_loop_policy", calls.append)
    configure_event_loop()
    assert calls == [sentinel]


@pytest.mark.parametrize("once", [True, False])
async def test_worker_startup_recovers_before_polling(monkeypatch, once):
    from contextlib import asynccontextmanager

    from app import worker
    from app.jobs import import_job

    events = []

    async def recover():
        events.append("recover")

    class FakeApp:
        @asynccontextmanager
        async def open_async(self):
            events.append("open")
            yield

        async def run_worker_async(self, **kwargs):
            assert kwargs == {"queues": ["imports"], "concurrency": 1, "wait": not once}
            events.append("run")

    monkeypatch.setattr(import_job, "recover_stalled", recover)
    monkeypatch.setattr(worker, "create_app", FakeApp)
    await worker.main(once)
    assert events == ["recover", "open", "run"]


@pytest.mark.parametrize("recover", [True, False])
async def test_transient_retry_backoff_and_limit(worker_env, monkeypatch, recover):
    from app.modules.imports import service

    client, book, sessions, queue = worker_env
    calls = 0
    original = service.stage_rows

    async def unstable(*args, **kwargs):
        nonlocal calls
        calls += 1
        if not recover or calls == 1:
            raise ConnectionError("simulated database outage")
        return await original(*args, **kwargs)

    monkeypatch.setattr(service, "stage_rows", unstable)
    job_id = (await upload(client, book)).json()["id"]
    for attempt in range(4):
        await drain(queue)
        async with sessions() as db, db.begin():
            state, scheduled = (
                await db.execute(
                    text("SELECT status,scheduled_at FROM procrastinate.procrastinate_jobs LIMIT 1")
                )
            ).one()
            if attempt == 0:
                assert state == "todo" and scheduled > datetime.now(UTC)
            await db.execute(
                text(
                    "UPDATE procrastinate.procrastinate_jobs SET scheduled_at=now() WHERE status='todo'"
                )
            )
        job = (await client.get(f"/api/v1/imports/{job_id}")).json()
        if job["status"] in {"review", "failed"}:
            break
    if recover:
        assert calls == 2 and job["status"] == "review"
    else:
        assert calls == 4 and job["error"] == "DATABASE_RETRY_EXHAUSTED"
    async with sessions() as db:
        assert await db.scalar(select(func.count()).select_from(ImportRow)) == (1 if recover else 0)


async def test_retry_when_state_persistence_also_loses_connection(worker_env, monkeypatch):
    from app.jobs import import_job
    from app.modules.imports import service

    client, book, sessions, queue = worker_env
    stage = service.stage_rows
    persist = import_job.fail_or_retry
    failed = False

    async def unstable_stage(*args, **kwargs):
        nonlocal failed
        if not failed:
            failed = True
            raise ConnectionError("database unavailable during staging")
        return await stage(*args, **kwargs)

    async def unavailable_persistence(*args, **kwargs):
        raise ConnectionError("database still unavailable")

    monkeypatch.setattr(service, "stage_rows", unstable_stage)
    monkeypatch.setattr(import_job, "fail_or_retry", unavailable_persistence)
    job_id = (await upload(client, book)).json()["id"]
    await drain(queue)
    assert (await client.get(f"/api/v1/imports/{job_id}")).json()["status"] == "processing"
    monkeypatch.setattr(import_job, "fail_or_retry", persist)
    async with sessions() as db, db.begin():
        await db.execute(
            text(
                "UPDATE procrastinate.procrastinate_jobs SET scheduled_at=now() WHERE status='todo'"
            )
        )
    await drain(queue)
    assert (await client.get(f"/api/v1/imports/{job_id}")).json()["status"] == "review"
