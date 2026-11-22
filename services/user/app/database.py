from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from .config import settings

_client: AsyncIOMotorClient | None = None


async def connect_db() -> None:
    global _client
    _client = AsyncIOMotorClient(settings.MONGO_URI)
    db = get_db()
    await db.users.create_index("email", unique=True)
    await db.users.create_index("user_id", unique=True)


async def close_db() -> None:
    global _client
    if _client is not None:
        _client.close()
        _client = None


def get_db() -> AsyncIOMotorDatabase:
    if _client is None:
        raise RuntimeError("Database client is not initialized")
    return _client[settings.MONGO_DB]