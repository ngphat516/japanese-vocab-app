import argparse
import asyncio
import json
from pathlib import Path

from app.db.session import Session
from app.modules.dictionary.service import seed_hanviet, seed_kanjidic  # noqa: F401


async def main(args):
    population = None
    if args.kanjidic2:
        document = json.loads(Path(args.kanjidic2).read_text(encoding="utf-8-sig"))
        population = {row["literal"] for row in document["characters"]}
    async with Session.begin() as db:
        print(await seed_hanviet(db, args.path, args.overrides, population=population))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("path", nargs="?", default="data/hanviet.csv")
    parser.add_argument("--kanjidic")
    parser.add_argument("--kanjidic2", help="Restrict Hán Việt population to this KANJIDIC2 JSON")
    parser.add_argument("--overrides", default="data/hanviet_overrides.csv")
    asyncio.run(main(parser.parse_args()))
