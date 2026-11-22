from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from app.core.config import get_settings

_client: AsyncIOMotorClient | None = None


async def connect_mongo() -> None:
    global _client
    settings = get_settings()
    _client = AsyncIOMotorClient(settings.mongo_uri)
    db = get_database()
    await db.bookings.create_index([("show_id", 1), ("status", 1)])
    await db.bookings.create_index([("user_id", 1), ("created_at", -1)])
    await db.bookings.create_index([("status", 1), ("hold_expires_at", 1)])


async def close_mongo() -> None:
    global _client
    if _client is not None:
        _client.close()
        _client = None


def get_database() -> AsyncIOMotorDatabase:
    if _client is None:
        raise RuntimeError("MongoDB client has not been initialized")
    settings = get_settings()
    return _client[settings.mongo_db_name]