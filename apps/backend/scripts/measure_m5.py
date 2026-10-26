"""Real HTTP + separate API/worker: 1,000 source CSV rows; clean temporary book/jobs."""

import asyncio
import csv
import hashlib
import io
import json
import os
import subprocess
import sys
import time
import uuid
from collections import Counter
from pathlib import Path

import httpx
import psutil
from sqlalchemy import func, select, text

from app import models  # noqa: F401
from app.core.config import get_settings
from app.core.security import token
from app.db.session import Session, engine
from app.modules.dictionary.models import Word
from app.modules.textbooks.models import Entry, Lesson, Textbook


async def source_csv():
    async with Session() as db:
        owner = await db.scalar(
            select(Textbook.owner_id)
            .where(Textbook.name.ilike("%Mimi%Kara%"))
            .order_by(Textbook.id)
            .limit(1)
        )
        pairs = (await db.execute(select(Word.kanji, Word.kana_norm))).all()
        unique = Counter(pairs)
        rows = (
            await db.execute(
                select(Word, Entry.content)
                .join(Entry, Entry.word_id == Word.id)
                .join(Lesson, Lesson.id == Entry.lesson_id)
                .join(Textbook, Textbook.id == Lesson.textbook_id)
                .where(Textbook.owner_id == owner, Word.kanji != "")
                .order_by(Word.id, Entry.id)
            )
        ).all()
        words_before = await db.scalar(select(func.count()).select_from(Word))
    selected, seen = [], set()
    for word, content in rows:
        if word.id in seen or unique[(word.kanji, word.kana_norm)] != 1:
            continue
        meaning = next((b for b in content if b["type"] == "meaning"), {})
        example = next((b for b in content if b["type"] == "example"), {})
        if not (meaning.get("vi") or meaning.get("en") or example.get("ja")):
            continue
        seen.add(word.id)
        index = len(selected)
        selected.append(
            [
                index // 50 + 1,
                index % 50 + 1,
                word.kanji,
                word.kana,
                meaning.get("vi", ""),
                meaning.get("en", ""),
                example.get("ja", ""),
                example.get("vi", ""),
                "",
            ]
        )
        if len(selected) == 1000:
            break
    assert len(selected) == 1000, "Need 1000 real unambiguous source words"
    output = io.StringIO(newline="")
    writer = csv.writer(output)
    writer.writerow(
        [
            "lesson",
            "order",
            "kanji",
            "kana",
            "meaning_vi",
            "meaning_en",
            "example_ja",
            "example_vi",
            "note",
        ]
    )
    writer.writerows(selected)
    return owner, output.getvalue().encode("utf-8-sig"), words_before


def actual_process(process):
    root = psutil.Process(process.pid)
    candidates = [root, *root.children(recursive=True)]
    return max(candidates, key=lambda p: p.memory_info().rss)


def stop(process):
    if process is None:
        return
    try:
        root = psutil.Process(process.pid)
        children = root.children(recursive=True)
        for item in [*children, root]:
            item.terminate()
        _, live = psutil.wait_procs([*children, root], timeout=5)
        for item in live:
            item.kill()
    except psutil.NoSuchProcess:
        pass


async def wait_state(client, job_id, expected, deadline=120, worker=None):
    start = time.perf_counter()
    observed = []
    while time.perf_counter() - start < deadline:
        if worker is not None and worker.poll() is not None:
            raise RuntimeError("Worker exited; inspect verification/m5/worker.log")
        response = await client.get(f"/api/v1/imports/{job_id}")
        response.raise_for_status()
        job = response.json()
        point = {
            "status": job["status"],
            "progress": job["progress"],
            "updated_at": job["updated_at"],
        }
        if not observed or point != observed[-1]:
            observed.append(point)
        if job["status"] == expected:
            return job, observed
        if job["status"] == "failed":
            raise RuntimeError("Import failed: " + str(job["error"]))
        await asyncio.sleep(0.05)
    raise TimeoutError("Import did not reach " + expected)


async def measure():
    output = Path("verification/m5")
    output.mkdir(parents=True, exist_ok=True)
    owner, payload, words_before = await source_csv()
    (output / "import-1000.csv").write_bytes(payload)
    settings = get_settings()
    env = {
        **os.environ,
        "IMPORT_MODE": "async",
        "RATE_LIMIT_ENABLED": "false",
        "PYTHONUTF8": "1",
        "DATABASE_URL": settings.database_url,
        "JWT_SECRET": settings.jwt_secret,
    }
    flags = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
    api = worker = None
    book_id = job_id = None
    resources = []
    monitor = None
    report = {
        "rows": 1000,
        "csv_sha256": hashlib.sha256(payload).hexdigest(),
        "transport": "uvicorn loopback HTTP, separate Procrastinate worker; polling 50ms",
        "mode": "async",
    }
    with (
        (output / "api.log").open("w", encoding="utf-8") as api_log,
        (output / "worker.log").open("w", encoding="utf-8") as worker_log,
    ):
        try:
            api = await asyncio.to_thread(
                subprocess.Popen,
                [
                    sys.executable,
                    "-m",
                    "uvicorn",
                    "app.main:app",
                    "--host",
                    "127.0.0.1",
                    "--port",
                    "8770",
                    "--workers",
                    "1",
                ],
                env=env,
                stdout=api_log,
                stderr=subprocess.STDOUT,
                creationflags=flags,
            )
            async with httpx.AsyncClient(
                base_url="http://127.0.0.1:8770",
                timeout=30,
                headers={"Authorization": "Bearer " + token(owner, "access")[0]},
            ) as client:
                for _ in range(200):
                    try:
                        if (await client.get("/health")).status_code == 200:
                            break
                    except httpx.HTTPError:
                        pass
                    await asyncio.sleep(0.1)
                else:
                    raise RuntimeError("API failed to start")
                warm = await client.get("/api/v1/search", params={"q": "緊張"})
                warm.raise_for_status()
                worker = await asyncio.to_thread(
                    subprocess.Popen,
                    [sys.executable, "-m", "app.worker"],
                    env=env,
                    stdout=worker_log,
                    stderr=subprocess.STDOUT,
                    creationflags=flags,
                )

                async def sample_rss():
                    while True:
                        try:
                            ap, wp = actual_process(api), actual_process(worker)
                            ar, wr = ap.memory_info().rss, wp.memory_info().rss
                            resources.append(
                                {
                                    "api_pid": ap.pid,
                                    "worker_pid": wp.pid,
                                    "api": ar,
                                    "worker": wr,
                                    "total": ar + wr,
                                }
                            )
                        except psutil.NoSuchProcess:
                            pass
                        await asyncio.sleep(0.05)

                monitor = asyncio.create_task(sample_rss())
                response = await client.post(
                    "/api/v1/textbooks", json={"name": "__m5_measure_" + uuid.uuid4().hex}
                )
                response.raise_for_status()
                book_id = response.json()["id"]
                start = time.perf_counter()
                response = await client.post(
                    "/api/v1/imports",
                    data={"textbook_id": str(book_id), "adapter": "csv_template"},
                    files={"file": ("real-1000.csv", payload, "text/csv")},
                )
                assert response.status_code == 202, response.text
                job_id = response.json()["id"]
                staged, parse_states = await wait_state(client, job_id, "review", worker=worker)
                report["upload_to_review_seconds"] = time.perf_counter() - start
                assert staged["total"] == 1000 and staged["ambiguous"] == 0
                commit_start = time.perf_counter()
                response = await client.post(f"/api/v1/imports/{job_id}/commit")
                assert response.status_code == 202, response.text
                done, commit_states = await wait_state(client, job_id, "done", worker=worker)
                report["commit_to_done_seconds"] = time.perf_counter() - commit_start
                report["end_to_end_seconds"] = time.perf_counter() - start
                report["progress"] = {"parse": parse_states, "commit": commit_states}
                assert done["progress"] == {"processed": 1000, "total": 1000}
                async with Session() as db:
                    count = await db.scalar(
                        select(func.count())
                        .select_from(Entry)
                        .join(Lesson, Lesson.id == Entry.lesson_id)
                        .where(Lesson.textbook_id == book_id)
                    )
                    assert count == 1000
                    report["entries_verified"] = count
                await asyncio.sleep(0.2)
                report["rss_final"] = resources[-1]
                report["rss_peak"] = {
                    key: max(r[key] for r in resources) for key in ["api", "worker", "total"]
                }
                response = await client.delete(f"/api/v1/textbooks/{book_id}")
                response.raise_for_status()
                book_id = None
        finally:
            if monitor:
                monitor.cancel()
                await asyncio.gather(monitor, return_exceptions=True)
            await asyncio.to_thread(stop, worker)
            await asyncio.to_thread(stop, api)
            async with Session() as db, db.begin():
                if book_id is not None:
                    book = await db.get(Textbook, book_id)
                    if book and book.name.startswith("__m5_measure_"):
                        await db.delete(book)
                if job_id is not None:
                    await db.execute(
                        text(
                            "DELETE FROM procrastinate.procrastinate_jobs WHERE args->>'job_id'=:id"
                        ),
                        {"id": str(job_id)},
                    )
                assert await db.scalar(select(func.count()).select_from(Word)) == words_before
            await engine.dispose()
    (output / "resources.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps({k: v for k, v in report.items() if k != "progress"}, indent=2))


if __name__ == "__main__":
    asyncio.run(measure())
