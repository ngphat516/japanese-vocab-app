import argparse
import asyncio

from app.db.session import Session
from app.modules.dictionary.service import seed_jmdict, seed_kanjidic


async def main(args):
    async with Session.begin() as db:
        await seed_jmdict(db, args.path)
        if args.kanjidic:
            await seed_kanjidic(db, args.kanjidic)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("path", nargs="?", default="data/jmdict.json")
    parser.add_argument("--kanjidic")
    asyncio.run(main(parser.parse_args()))
