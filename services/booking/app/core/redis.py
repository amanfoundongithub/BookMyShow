from redis.asyncio import Redis
from app.core.config import get_settings

_redis: Redis | None = None


async def connect_redis() -> None:
    global _redis
    settings = get_settings()
    _redis = Redis.from_url(settings.redis_url, decode_responses=True)


async def close_redis() -> None:
    global _redis
    if _redis is not None:
        await _redis.aclose()
        _redis = None


def get_redis() -> Redis:
    if _redis is None:
        raise RuntimeError("Redis client has not been initialized")
    return _redis