"""Paired c=1 comparison on the same seeded DB, isolating the saved-page lookup."""

import argparse
import asyncio
import importlib.util
import json
import logging
import math
import os
import statistics
import subprocess
import tempfile
import time
from pathlib import Path

from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from testcontainers.community.postgres import PostgresContainer

from scripts.bench_search import QUERIES, measure


async def compare(url, args, baseline):
    from app.core.security import token
    from app.db.session import get_db
    from app.main import app
    from app.modules.search import service

    # Reuse the production benchmark loader (200k synthetic or full JMdict +12k entries).
    warmup = args.output.with_suffix(".warmup.json")
    await measure(url, warmup, QUERIES[:7], 1, args.jmdict)
    engine = create_async_engine(url, pool_size=1, max_overflow=0)
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    async with engine.begin() as db:
        await db.execute(
            text(
                "INSERT INTO saved_words(user_id,word_id,note,tags) SELECT 1,id,'','{}' FROM words ORDER BY id LIMIT 1000"
            )
        )
        await db.execute(text("ANALYZE saved_words"))
        await db.execute(text("SELECT gin_clean_pending_list('ix_entries_example_lemmas')"))

    async def dependency():
        async with sessions() as db, db.begin():
            yield db

    app.dependency_overrides[get_db] = dependency
    after = service.search
    report = {
        "metadata": {
            "baseline_ref": args.baseline_ref,
            "dataset": "jmdict-full-eng" if args.jmdict else "synthetic",
            "entries": 12000,
            "saved_words": 1000,
            "iterations": args.iterations,
            "concurrency": 1,
            "method": "paired, alternating order, same DB/process; warmup excluded",
        }
    }
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://bench",
            headers={"Authorization": "Bearer " + token(1, "access")[0]},
        ) as http:
            for query in QUERIES[:7]:
                timings = {"before": [], "after": []}
                statuses = {"before": [], "after": []}
                totals = {"before": [], "after": []}
                for index in range(args.iterations):
                    for phase in ["before", "after"] if index % 2 == 0 else ["after", "before"]:
                        service.search = baseline if phase == "before" else after
                        start = time.perf_counter()
                        response = await http.get("/api/v1/search", params={"q": query, "size": 20})
                        timings[phase].append((time.perf_counter() - start) * 1000)
                        statuses[phase].append(response.status_code)
                        response.raise_for_status()
                        totals[phase].append(response.json()["total"])
                report[query] = {
                    phase: {
                        "p95_ms": sorted(values)[math.ceil(0.95 * len(values)) - 1],
                        "median_ms": statistics.median(values),
                        "samples_ms": values,
                        "statuses": statuses[phase],
                    }
                    for phase, values in timings.items()
                }
                assert totals["before"] == totals["after"]
                delta = report[query]["after"]["p95_ms"] - report[query]["before"]["p95_ms"]
                report[query]["delta_p95_ms"] = delta
                print(
                    query.encode("unicode_escape").decode(), f"delta_p95_ms={delta:.2f}", flush=True
                )
                args.output.write_text(
                    json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
                )
    finally:
        service.search = after
        app.dependency_overrides.clear()
        await engine.dispose()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--jmdict", type=Path)
    parser.add_argument("--iterations", type=int, default=20)
    parser.add_argument("--baseline-ref", default="fa3a07b")
    args = parser.parse_args()
    os.environ["RATE_LIMIT_ENABLED"] = "false"
    logging.disable(logging.INFO)
    source = subprocess.check_output(
        ["git", "show", f"{args.baseline_ref}:apps/backend/app/modules/search/service.py"]
    )
    with (
        tempfile.TemporaryDirectory(prefix="pre-saved-") as directory,
        PostgresContainer("pgvector/pgvector:pg16", dbname="vocab_bench") as pg,
    ):
        path = Path(directory) / "search.py"
        path.write_bytes(source)
        spec = importlib.util.spec_from_file_location("app.modules.search._pre_saved", path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        url = pg.get_connection_url().replace("postgresql+psycopg2", "postgresql+asyncpg")
        subprocess.run(
            [os.sys.executable, "-m", "alembic", "upgrade", "head"],
            check=True,
            env={**os.environ, "DATABASE_URL": url},
        )
        asyncio.run(compare(url, args, module.search))


if __name__ == "__main__":
    main()
