"""Repeatable HTTP benchmark on an ephemeral PostgreSQL vocab_bench database.

Run: python -m scripts.bench_search --output verification/bench-before.json
The container and its database are removed even if a request fails. Never uses .env DB.
"""

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

from testcontainers.community.postgres import PostgresContainer

QUERIES = ["きんちょう", "kinchou", "緊張", "căng thẳng", "school", "い", "a"]


async def measure(url, output, queries, iterations):
    from httpx import ASGITransport, AsyncClient
    from sqlalchemy import event, text
    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

    from app.core.security import token
    from app.db.session import get_db
    from app.main import app

    engine = create_async_engine(url)
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    async with engine.begin() as db:
        await db.execute(
            text("""
            INSERT INTO users(id,email,password_hash,display_name,role)
            VALUES (1,'bench@example.com','unused','Benchmark','admin');
        """)
        )
        await db.execute(
            text("""
            INSERT INTO words(id,kanji,kana,kana_norm,romaji,hanviet,pos)
            SELECT n, '試験' || n, 'い' || n, 'い' || n, 'i' || n, '', '{}'
            FROM generate_series(1,200000) n
        """)
        )
        await db.execute(
            text("""
            UPDATE words SET kanji='緊張',kana='きんちょう',kana_norm='きんちょう',
            romaji='kinchou' WHERE id=1
        """)
        )
        await db.execute(
            text("""
            INSERT INTO word_senses(word_id,lang,gloss,"order")
            SELECT n, 'en', CASE WHEN n=1 THEN 'tension' WHEN n%97=0 THEN 'school'
                ELSE 'invented meaning ' || n END, 0 FROM generate_series(1,200000) n
            UNION ALL
            SELECT n, 'vi', CASE WHEN n=1 THEN 'căng thẳng'
                ELSE 'invented alternative ' || n END, 1 FROM generate_series(1,200000) n
        """)
        )
        await db.execute(
            text("""
            INSERT INTO textbooks(id,name,visibility,owner_id) VALUES (1,'Benchmark','private',1)
        """)
        )
        await db.execute(
            text("""
            INSERT INTO lessons(id,textbook_id,number,title) VALUES(1,1,1,'Benchmark lesson')
        """)
        )
        await db.execute(
            text("""
            INSERT INTO textbook_entries(word_id,lesson_id,order_no,content,search_text)
            SELECT n,1,n,'[{"type":"meaning","en":"invented benchmark"}]'::jsonb,
            CASE WHEN n=1 THEN 'căng thẳng' ELSE 'invented benchmark ' || n END
            FROM generate_series(1,12000) n
        """)
        )
        await db.execute(text("ANALYZE"))

    async def db_override():
        async with sessions() as db, db.begin():
            await db.execute(text("SET LOCAL statement_timeout = '5s'"))
            yield db

    captured = []

    @event.listens_for(engine.sync_engine, "before_cursor_execute")
    def before(conn, cursor, statement, parameters, context, executemany):
        context.bench_start = time.perf_counter()

    @event.listens_for(engine.sync_engine, "after_cursor_execute")
    def after(conn, cursor, statement, parameters, context, executemany):
        if statement.lstrip().upper().startswith("SELECT"):
            captured.append((time.perf_counter() - context.bench_start, statement, parameters))

    app.dependency_overrides[get_db] = db_override
    report = {}
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app, raise_app_exceptions=False),
            base_url="http://bench",
            headers={"Authorization": "Bearer " + token(1, "access")[0]},
        ) as http:
            for query in queries:
                durations = []
                statuses = []
                for _ in range(iterations):
                    start = time.perf_counter()
                    response = await http.get("/api/v1/search", params={"q": query, "size": 20})
                    statuses.append(response.status_code)
                    durations.append((time.perf_counter() - start) * 1000)
                report[query] = {
                    "median_ms": statistics.median(durations),
                    "p95_ms": sorted(durations)[math.ceil(0.95 * len(durations)) - 1],
                    "max_ms": max(durations),
                    "total": response.json().get("total"),
                    "statuses": statuses,
                    "samples_ms": durations,
                }
                Path(output).write_text(
                    json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
                )
                print(query.encode("unicode_escape").decode(), report[query], flush=True)
        _, statement, parameters = max(captured, key=lambda item: item[0])
        report["slowest_sql"] = statement
        report["sql_timings"] = [
            {"duration_ms": duration * 1000, "sql": sql}
            for duration, sql, _ in sorted(captured, key=lambda item: item[0], reverse=True)[:5]
        ]
        async with engine.connect() as db:
            await db.exec_driver_sql("SET statement_timeout = '60s'")
            await db.exec_driver_sql("SET work_mem = '16MB'")
            await db.exec_driver_sql("SET pg_trgm.similarity_threshold = 0.3")
            await db.exec_driver_sql("SET plan_cache_mode = force_custom_plan")
            plan = await db.exec_driver_sql("EXPLAIN (ANALYZE, BUFFERS) " + statement, parameters)
            report["slowest_sql"] = statement
            report["explain"] = list(plan.scalars())
        Path(output).write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        print(json.dumps(report, ensure_ascii=True, indent=2))
    finally:
        app.dependency_overrides.clear()
        await engine.dispose()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", default="verification/bench-search.json")
    parser.add_argument("--queries", nargs="+", default=QUERIES)
    parser.add_argument("--iterations", type=int, default=20)
    parser.add_argument(
        "--baseline", action="store_true", help="Use committed P0 search orchestration"
    )
    args = parser.parse_args()
    os.environ["RATE_LIMIT_ENABLED"] = "false"
    os.environ.setdefault("JWT_SECRET", "benchmark-only-secret-at-least-32-characters")
    logging.disable(logging.INFO)
    with PostgresContainer("pgvector/pgvector:pg16", dbname="vocab_bench") as pg:
        url = pg.get_connection_url().replace("postgresql+psycopg2", "postgresql+asyncpg")
        subprocess.run(
            [os.sys.executable, "-m", "alembic", "upgrade", "head"],
            check=True,
            env={**os.environ, "DATABASE_URL": url},
        )
        with tempfile.TemporaryDirectory(prefix="vocab-bench-") as directory:
            if args.baseline:
                from app.modules.search import service

                source = subprocess.check_output(
                    [
                        "git",
                        "show",
                        "deb52bc3306cfbba41d00efaff8883e9eb1c1856:apps/backend/app/modules/search/service.py",
                    ]
                )
                path = Path(directory) / "baseline.py"
                path.write_bytes(source)
                spec = importlib.util.spec_from_file_location("baseline_search", path)
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                service.search = module.search
            asyncio.run(measure(url, args.output, args.queries, args.iterations))


if __name__ == "__main__":
    main()
