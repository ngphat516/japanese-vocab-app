"""20,000 self-authored characters, real HTTP upload -> async review; clean probes."""

import asyncio
import hashlib
import json
import os
import subprocess
import sys
import time
import uuid
from pathlib import Path

import httpx
from sqlalchemy import select, text

from app import models  # noqa: F401
from app.core.config import get_settings
from app.core.security import token
from app.db.session import Session, engine
from app.modules.textbooks.models import Textbook
from scripts.measure_m5 import stop, wait_state


async def measure():
    output = Path("verification/m6")
    output.mkdir(parents=True, exist_ok=True)
    unit = (
        "今日は図書館で日本語の本を読みました。新しい言葉を覚えて、友達と静かに話します。\n"
        "朝は野菜を食べて、お茶を飲みます。学校へ歩いて行き、先生に質問しました。\n"
        "休みの日には公園で走ります。雨が降ったので、部屋で音楽を聞きました。\n"
        "仕事が終わったら料理を作ります。明日は早く起きて、駅で友達を待ちます。\n"
    )
    passage = (unit * (20000 // len(unit) + 1))[:20000]
    (output / "free-text-20000.txt").write_text(passage, encoding="utf-8")
    async with Session() as db:
        owner = await db.scalar(select(Textbook.owner_id).order_by(Textbook.id).limit(1))
    settings = get_settings()
    env = {
        **os.environ,
        "DATABASE_URL": settings.database_url,
        "JWT_SECRET": settings.jwt_secret,
        "IMPORT_MODE": "async",
        "RATE_LIMIT_ENABLED": "false",
        "PYTHONUTF8": "1",
    }
    flags = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
    api = worker = None
    book_id = None
    job_ids = []
    report = {
        "characters": len(passage),
        "sha256": hashlib.sha256(passage.encode()).hexdigest(),
        "transport": "uvicorn loopback, separate Procrastinate process, 50ms poll",
        "warmup": "API /health only; first worker run includes lazy tokenizer load",
        "samples_seconds": [],
    }
    with (
        (output / "api.log").open("w", encoding="utf-8") as alog,
        (output / "worker.log").open("w", encoding="utf-8") as wlog,
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
                    "8771",
                ],
                env=env,
                stdout=alog,
                stderr=subprocess.STDOUT,
                creationflags=flags,
            )
            async with httpx.AsyncClient(
                base_url="http://127.0.0.1:8771",
                headers={"Authorization": "Bearer " + token(owner, "access")[0]},
                timeout=30,
            ) as client:
                for _ in range(200):
                    try:
                        if (await client.get("/health")).status_code == 200:
                            break
                    except httpx.HTTPError:
                        pass
                    await asyncio.sleep(0.1)
                else:
                    raise RuntimeError("API did not start")
                worker = await asyncio.to_thread(
                    subprocess.Popen,
                    [sys.executable, "-m", "app.worker"],
                    env=env,
                    stdout=wlog,
                    stderr=subprocess.STDOUT,
                    creationflags=flags,
                )
                response = await client.post(
                    "/api/v1/textbooks", json={"name": "__m6_measure_" + uuid.uuid4().hex}
                )
                response.raise_for_status()
                book_id = response.json()["id"]
                for _ in range(3):
                    start = time.perf_counter()
                    response = await client.post(
                        "/api/v1/imports",
                        data={"textbook_id": str(book_id), "adapter": "free_text"},
                        files={"file": ("source.txt", passage.encode(), "text/plain")},
                    )
                    assert response.status_code == 202, response.text
                    job_id = response.json()["id"]
                    job_ids.append(job_id)
                    job, _ = await wait_state(client, job_id, "review", worker=worker)
                    report["samples_seconds"].append(time.perf_counter() - start)
                    report["vocabulary_rows"] = job["total"]
                    rows = (
                        await client.get(f"/api/v1/imports/{job_id}/rows", params={"size": 100})
                    ).json()
                    assert rows["total"] == job["total"] and job["total"] > 0
                report["max_seconds"] = max(report["samples_seconds"])
                response = await client.delete(f"/api/v1/textbooks/{book_id}")
                response.raise_for_status()
                book_id = None
        finally:
            await asyncio.to_thread(stop, worker)
            await asyncio.to_thread(stop, api)
            async with Session() as db, db.begin():
                if book_id is not None:
                    book = await db.get(Textbook, book_id)
                    if book and book.name.startswith("__m6_measure_"):
                        await db.delete(book)
                for job_id in job_ids:
                    await db.execute(
                        text(
                            "DELETE FROM procrastinate.procrastinate_jobs WHERE args->>'job_id'=:id"
                        ),
                        {"id": str(job_id)},
                    )
            await engine.dispose()
    (output / "resources.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    asyncio.run(measure())
