"""python -m app.worker: PostgreSQL Procrastinate import worker."""

import argparse
import asyncio
import sys


def configure_event_loop():
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())


def create_app(url=None, sessions=None):
    import procrastinate

    from app.core.config import get_settings
    from app.jobs.import_job import register

    url = (url or get_settings().database_url).replace("postgresql+asyncpg://", "postgresql://")
    app = procrastinate.App(
        connector=procrastinate.PsycopgConnector(
            conninfo=url,
            min_size=1,
            max_size=2,
            kwargs={"options": "-c search_path=procrastinate,public", "connect_timeout": 5},
        )
    )
    register(app, **({"sessions": sessions} if sessions is not None else {}))
    return app


async def main(once=False):
    from app.jobs.import_job import recover_stalled

    await recover_stalled()
    app = create_app()
    async with app.open_async():
        await app.run_worker_async(queues=["imports"], concurrency=1, wait=not once)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--once", action="store_true")
    configure_event_loop()
    asyncio.run(main(parser.parse_args().once))
