"""Seed the catalog data in MongoDB. Run with `.venv/bin/python scripts/seed_db.py`."""

import asyncio
import os
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
os.chdir(ROOT_DIR)
sys.path.insert(0, str(ROOT_DIR / "services/catalog"))

from motor.motor_asyncio import AsyncIOMotorClient

from app.core.config import get_settings
from app.services.seed import seed_catalog


async def main() -> None:
    settings = get_settings()
    client = AsyncIOMotorClient(settings.mongo_uri)
    try:
        await client.admin.command("ping")
        db = client[settings.mongo_db_name]
        await seed_catalog(db)
        counts = {
            collection: await db[collection].count_documents({})
            for collection in ("cities", "cinemas", "halls", "movies", "shows")
        }
        print(f"Seeded catalog data in {db.name}: {counts}")
    finally:
        client.close()


if __name__ == "__main__":
    asyncio.run(main())
