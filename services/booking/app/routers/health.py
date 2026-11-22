from fastapi import APIRouter, HTTPException, status
from app.core.db import get_database
from app.core.redis import get_redis

router = APIRouter(tags=["health"])


@router.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "service": "booking-service"}


@router.get("/ready")
async def ready() -> dict[str, str]:
    try:
        db = get_database()
        await db.command("ping")
        redis = get_redis()
        await redis.ping()
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Dependencies not ready: {exc}",
        ) from exc
    return {"status": "ready"}