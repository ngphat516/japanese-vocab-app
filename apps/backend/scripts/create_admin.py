import argparse
import asyncio

from sqlalchemy import select

from app.db.session import Session
from app.modules.auth.models import User


async def main(email):
    async with Session.begin() as db:
        user = await db.scalar(select(User).where(User.email == email.lower()))
        if not user:
            raise SystemExit("Register account first")
        user.role = "admin"


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("email")
    asyncio.run(main(parser.parse_args().email))
