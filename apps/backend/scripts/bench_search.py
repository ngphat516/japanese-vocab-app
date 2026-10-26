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

QUERIES = [
    "きんちょう",
    "kinchou",
    "緊張",
    "căng thẳng",
    "school",
    "い",
    "a",
    "行かなかった",
    "緊張して",
]


async def measure(url, output, queries, iterations, jmdict=None, concurrency=1, baseline_ref=None):
    from httpx import ASGITransport, AsyncClient
    from sqlalchemy import event, text
    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

    from app.core.security import token
    from app.db.session import get_db
    from app.main import app

    engine = create_async_engine(url, pool_size=10, max_overflow=0)
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    async with engine.begin() as db:
        await db.execute(
            text("""
            INSERT INTO users(id,email,password_hash,display_name,role)
            VALUES (1,'bench@example.com','unused','Benchmark','admin');
        """)
        )
        if jmdict:
            from scripts.bench_seed import seed_full_jmdict

            metadata = await seed_full_jmdict(db, jmdict)
        else:
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
                text(
                    "UPDATE words SET kanji='行く',kana='いく',kana_norm='いく',romaji='iku' WHERE id=2"
                )
            )
            metadata = {"dataset": "synthetic", "words": 200000, "senses": 400000}
        from scripts.bench_seed import seed_examples

        metadata["entries"] = await seed_examples(db)
        example_word_id = await db.scalar(
            text(
                "SELECT id FROM words WHERE kanji='緊張' AND kana_norm='きんちょう' ORDER BY id LIMIT 1"
            )
        )
        metadata["example_word_id"] = example_word_id
        metadata["baseline_ref"] = baseline_ref
        # Finish bulk-load GIN maintenance before timing. Otherwise pending-list
        # cleanup by autovacuum at an arbitrary point changes the count plans.
        metadata["lemma_gin_pending_pages_cleaned"] = await db.scalar(
            text("SELECT gin_clean_pending_list('ix_entries_lemmas')")
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
        if statement.lstrip().upper().startswith(("SELECT", "WITH")):
            captured.append((time.perf_counter() - context.bench_start, statement, parameters))

    app.dependency_overrides[get_db] = db_override
    report = {"metadata": {**metadata, "concurrency": concurrency, "iterations": iterations}}
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app, raise_app_exceptions=False),
            base_url="http://bench",
            headers={"Authorization": "Bearer " + token(1, "access")[0]},
        ) as http:
            workloads = [(q, "/api/v1/search", {"q": q, "size": 20}) for q in queries]
            if not baseline_ref:
                workloads.append(
                    ("examples", f"/api/v1/words/{example_word_id}/examples", {"size": 20})
                )
            for query, endpoint, params in workloads:
                durations = []
                statuses = []

                async def request(endpoint=endpoint, params=params):
                    start = time.perf_counter()
                    response = await http.get(endpoint, params=params)
                    return (
                        response.status_code,
                        (time.perf_counter() - start) * 1000,
                        response.json(),
                    )

                bodies = []
                for offset in range(0, iterations, concurrency):
                    results = await asyncio.gather(
                        *(request() for _ in range(min(concurrency, iterations - offset)))
                    )
                    for status, duration, body in results:
                        statuses.append(status)
                        durations.append(duration)
                        bodies.append(body)
                report[query] = {
                    "median_ms": statistics.median(durations),
                    "p95_ms": sorted(durations)[math.ceil(0.95 * len(durations)) - 1],
                    "max_ms": max(durations),
                    "total": bodies[-1].get("total"),
                    "total_capped": bodies[-1].get("total_capped", False),
                    "errors": [b for b in bodies if "error" in b],
                    "statuses": statuses,
                    "samples_ms": durations,
                }
                Path(output).write_text(
                    json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
                )
                print(
                    query.encode("unicode_escape").decode(),
                    "p95_ms=",
                    round(report[query]["p95_ms"], 2),
                    "statuses=",
                    sorted(set(statuses)),
                    flush=True,
                )
        _, statement, parameters = max(captured, key=lambda item: item[0])
        report["slowest_sql"] = statement
        report["sql_timings"] = [
            {"duration_ms": duration * 1000, "sql": sql}
            for duration, sql, _ in sorted(captured, key=lambda item: item[0], reverse=True)[:5]
        ]
        async with engine.connect() as db:
            await db.begin()
            await db.exec_driver_sql("SET LOCAL statement_timeout = '60s'")
            await db.exec_driver_sql("SET LOCAL work_mem = '16MB'")
            plan = await db.exec_driver_sql("EXPLAIN (ANALYZE, BUFFERS) " + statement, parameters)
            report["slowest_sql"] = statement
            report["explain"] = list(plan.scalars())
        count_queries = [
            (sql, parameters)
            for _, sql, parameters in captured
            if "@>" in sql and "count(" in sql.lower()
        ]
        if count_queries:
            sql, parameters = count_queries[0]
            async with engine.connect() as db:
                plan = await db.exec_driver_sql("EXPLAIN (ANALYZE, BUFFERS) " + sql, parameters)
                report["example_count_sql"] = sql
                report["example_count_explain"] = list(plan.scalars())
        Path(output).write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        print("Saved", output, flush=True)
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
    parser.add_argument("--jmdict", type=Path, help="Full jmdict-simplified English JSON")
    parser.add_argument("--concurrency", type=int, choices=range(1, 11), default=1)
    parser.add_argument(
        "--baseline-ref", help="Load search/dictionary orchestration from this Git ref"
    )
    args = parser.parse_args()
    if args.iterations < 1:
        parser.error("iterations must be positive")
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
            if args.baseline_ref:
                from app.modules.dictionary import service as dictionary
                from app.modules.search import service as search

                for package, target in [("dictionary", dictionary), ("search", search)]:
                    source = subprocess.check_output(
                        [
                            "git",
                            "show",
                            f"{args.baseline_ref}:apps/backend/app/modules/{package}/service.py",
                        ]
                    )
                    path = Path(directory) / f"{package}_baseline.py"
                    path.write_bytes(source)
                    spec = importlib.util.spec_from_file_location(
                        f"app.modules.{package}._bench_baseline", path
                    )
                    module = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(module)
                    if package == "dictionary":
                        target.search_page = module.search_page
                    else:
                        target.search = module.search
            asyncio.run(
                measure(
                    url,
                    args.output,
                    args.queries,
                    args.iterations,
                    args.jmdict,
                    args.concurrency,
                    args.baseline_ref,
                )
            )


if __name__ == "__main__":
    main()
