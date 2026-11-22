from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from app.core.config import get_settings

_client: AsyncIOMotorClient | None = None


async def connect_db() -> None:
    global _client
    settings = get_settings()
    _client = AsyncIOMotorClient(settings.mongo_uri)
    db = get_database()
    await db.cinemas.create_index("cinema_id", unique=True)
    await db.cinemas.create_index("city_id")


async def close_db() -> None:
    global _client
    if _client is not None:
        _client.close()
        _client = None


def get_database() -> AsyncIOMotorDatabase:
    if _client is None:
        raise RuntimeError("Database client is not initialized")
    settings = get_settings()
    return _client[settings.mongo_db_name]