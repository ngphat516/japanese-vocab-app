import argparse
import asyncio

from app.db.session import Session
from app.modules.dictionary.service import seed_hanviet, seed_kanjidic  # noqa: F401


async def main(args):
    async with Session.begin() as db:
        await seed_hanviet(db, args.path)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("path", nargs="?", default="data/hanviet.csv")
    parser.add_argument("--kanjidic")
    asyncio.run(main(parser.parse_args()))
