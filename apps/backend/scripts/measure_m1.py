"""Read local Mimikara examples; export a manual sample and measure NLP/API RSS.

This script never updates entries. It launches a temporary uvicorn API on loopback.
"""

import argparse
import asyncio
import hashlib
import json
import platform
import random
import subprocess
import sys
import time
from pathlib import Path

import httpx
import psutil
from sqlalchemy import func, select, text

from app.core.security import token
from app.db.session import engine
from app.modules.textbooks.models import Entry, Lesson, Textbook
from app.nlp.furigana import add_furigana, strip_markup
from app.nlp.tokenizer import lemmas, tokenize


async def source_examples():
    async with engine.connect() as db, db.begin():
        await db.execute(text("SET TRANSACTION READ ONLY"))
        rows = (
            await db.execute(
                select(
                    Entry.id,
                    Entry.order_no,
                    Entry.content,
                    Textbook.id.label("book_id"),
                    Textbook.name,
                    Textbook.owner_id,
                )
                .join(Lesson, Entry.lesson_id == Lesson.id)
                .join(Textbook, Lesson.textbook_id == Textbook.id)
                .where(func.replace(func.lower(Textbook.name), " ", "").contains("mimikara"))
                .order_by(Entry.id)
            )
        ).all()
    await engine.dispose()
    return [
        {
            "entry_id": r.id,
            "order_no": r.order_no,
            "book_id": r.book_id,
            "book": r.name,
            "owner_id": r.owner_id,
            "ja": block["ja"],
        }
        for r in rows
        for block in r.content
        if block.get("type") == "example" and block.get("ja")
    ]


def api_rss(owner_id, output, port):
    pid_file = (output / "m1-api-probe.pid").resolve()
    pid_file.unlink(missing_ok=True)
    with (output / "m1-api-probe.log").open("w", encoding="utf-8") as log:
        child = subprocess.Popen(
            [
                sys.executable,
                "-m",
                "scripts.m1_api_probe",
                "--port",
                str(port),
                "--pid-file",
                str(pid_file),
            ],
            stdout=log,
            stderr=log,
        )
        try:
            with httpx.Client(base_url=f"http://127.0.0.1:{port}", timeout=30) as http:
                for _ in range(100):
                    if child.poll() is not None:
                        raise RuntimeError("API probe exited; inspect m1-api-probe.log")
                    try:
                        if http.get("/health").status_code == 200:
                            break
                    except httpx.ConnectError:
                        pass
                    time.sleep(0.1)
                else:
                    raise TimeoutError("API probe did not become healthy")
                response = http.get(
                    "/api/v1/search",
                    params={"q": "緊張"},
                    headers={
                        "Authorization": "Bearer " + token(owner_id, "access")[0],
                    },
                )
                response.raise_for_status()
                api_process = psutil.Process(int(pid_file.read_text(encoding="ascii")))
                return {
                    "rss_bytes": api_process.memory_info().rss,
                    "measured_pid": api_process.pid,
                    "search_status": response.status_code,
                    "sudachi_loaded": True,
                    "platform": platform.platform(),
                    "process": "uvicorn, one worker",
                }
        finally:
            if pid_file.exists():
                server = psutil.Process(int(pid_file.read_text(encoding="ascii")))
                server.terminate()
                server.wait(timeout=15)
            child.terminate()
            child.wait(timeout=15)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path("verification"))
    parser.add_argument("--port", type=int, default=8766)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    examples = asyncio.run(source_examples())
    if len(examples) < 30:
        raise RuntimeError("Need at least 30 real Mimikara examples")
    rng = random.Random(20261020)
    sample = rng.sample(examples, 30)
    source = rng.sample(examples, min(1000, len(examples)))
    workload = [strip_markup(source[i % len(source)]["ja"]).replace("__", "") for i in range(1000)]
    start = time.perf_counter()
    tokenize("緊張")
    load_seconds = time.perf_counter() - start
    start = time.perf_counter()
    lemma_results = [lemmas(value) for value in workload]
    lemma_seconds = time.perf_counter() - start
    start = time.perf_counter()
    furigana_results = [add_furigana(value) for value in workload]
    furigana_seconds = time.perf_counter() - start
    report = {
        "seed": 20261020,
        "available_examples": len(examples),
        "workload_sentences": 1000,
        "unique_source_examples": len(source),
        "dictionary_load_seconds": load_seconds,
        "lemma_seconds": lemma_seconds,
        "furigana_seconds": furigana_seconds,
        "combined_seconds": lemma_seconds + furigana_seconds,
        "workload_sha256": hashlib.sha256(
            json.dumps(workload, ensure_ascii=False).encode()
        ).hexdigest(),
        "api": api_rss(examples[0]["owner_id"], args.output, args.port),
        "lemma_count": sum(map(len, lemma_results)),
        "furigana_characters": sum(map(len, furigana_results)),
        "sample_status": "MANUAL",
        "nfr02": "NLP component only, not full import/matching",
    }
    lines = [
        "# Milestone 1 NLP sample — MANUAL",
        "",
        "Seed: 20261020. Read-only export; no content was corrected.",
        "",
    ]
    for i, row in enumerate(sample, 1):
        lines.extend(
            [
                f"## {i}. Entry {row['entry_id']}, order {row['order_no']}, textbook {row['book_id']}",
                "",
                "Original:",
                "",
                row["ja"],
                "",
                "add_furigana(original):",
                "",
                add_furigana(row["ja"]),
                "",
                "add_furigana(without existing markup):",
                "",
                add_furigana(strip_markup(row["ja"])),
                "",
                "Lemmas:",
                "",
                json.dumps(lemmas(strip_markup(row["ja"])), ensure_ascii=False),
                "",
            ]
        )
    (args.output / "m1_nlp_sample.md").write_text("\n".join(lines), encoding="utf-8")
    (args.output / "m1-resources.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps(report, ensure_ascii=True, indent=2))


if __name__ == "__main__":
    main()
