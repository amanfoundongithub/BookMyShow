"""Seed the default movie options in MongoDB without overwriting custom values."""

import asyncio
import os
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
os.chdir(ROOT_DIR)
sys.path.insert(0, str(ROOT_DIR / "services/movies"))

from motor.motor_asyncio import AsyncIOMotorClient

from app.core.config import get_settings
from app.core.movie_options import DEFAULT_MOVIE_OPTIONS, MOVIE_OPTIONS_ID


async def main() -> None:
    settings = get_settings()
    client = AsyncIOMotorClient(settings.mongo_uri)
    try:
        await client.admin.command("ping")
        db = client[settings.mongo_db_name]
        result = await db.movie_metadata.update_one(
            {"_id": MOVIE_OPTIONS_ID},
            {"$setOnInsert": DEFAULT_MOVIE_OPTIONS},
            upsert=True,
        )
        if result.upserted_id is not None:
            print(f"Seeded default movie options in {db.name}.movie_metadata")
        else:
            print(f"Movie options already exist in {db.name}.movie_metadata; left unchanged")
    finally:
        client.close()


if __name__ == "__main__":
    asyncio.run(main())
