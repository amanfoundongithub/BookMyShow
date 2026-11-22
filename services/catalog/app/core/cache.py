import json
from typing import Any
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


def get_redis() -> Redis | None:
    return _redis


async def cache_get_json(key: str) -> Any | None:
    if _redis is None:
        return None
    raw = await _redis.get(key)
    return json.loads(raw) if raw else None


async def cache_set_json(key: str, value: Any, ttl_seconds: int) -> None:
    if _redis is None:
        return
    await _redis.set(key, json.dumps(value, default=str), ex=ttl_seconds)


async def cache_delete_pattern(pattern: str) -> None:
    if _redis is None:
        return
    keys = [key async for key in _redis.scan_iter(match=pattern)]
    if keys:
        await _redis.delete(*keys)