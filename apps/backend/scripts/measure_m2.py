"""Measure the real single-worker uvicorn RSS after an M2 search request."""

import argparse
import asyncio
import json
from pathlib import Path

from scripts.measure_m1 import api_rss, source_examples


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path("verification/m2"))
    parser.add_argument("--port", type=int, default=8767)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    examples = asyncio.run(source_examples())
    report = {
        "api": api_rss(examples[0]["owner_id"], args.output, args.port),
        "scope": "Local snapshot after Sudachi load and authenticated search (M2 counts); not peak/deployed RSS",
    }
    (args.output / "resources.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps(report, ensure_ascii=True, indent=2))


if __name__ == "__main__":
    main()
