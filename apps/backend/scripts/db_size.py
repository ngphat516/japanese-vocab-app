"""Print database size and the largest tables (used to check hosted free-tier quotas)."""

import asyncio

import sqlalchemy as sa

from app.db.session import engine

TABLES = sa.text(
    "select relname, pg_size_pretty(pg_total_relation_size(relid)) "
    "from pg_statio_user_tables order by pg_total_relation_size(relid) desc limit 10"
)


async def main():
    async with engine.connect() as conn:
        total = await conn.execute(
            sa.text("select pg_size_pretty(pg_database_size(current_database()))")
        )
        print("database:", total.scalar())
        for name, size in await conn.execute(TABLES):
            print(f"  {name}: {size}")
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
