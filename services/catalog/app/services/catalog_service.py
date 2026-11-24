from datetime import datetime, timezone
from fastapi import HTTPException, status
import httpx
from motor.motor_asyncio import AsyncIOMotorDatabase
from app.core.cache import cache_delete_pattern, cache_get_json, cache_set_json
from app.core.config import get_settings
from app.models.schemas import (
    CinemaResponse,
    CreateShowRequest,
    CreateShowResponse,
    ShowResponse,
)


class CatalogService:
    def __init__(
        self,
        db: AsyncIOMotorDatabase,
        http_client: httpx.AsyncClient | None = None,
    ) -> None:
        self.db = db
        self.http_client = http_client
        self.settings = get_settings()

    @staticmethod
    def _parse_cinema(raw: dict) -> CinemaResponse | None:
        data = dict(raw)
        cinema_id = data.get("cinema_id") or data.get("_id")
        if not cinema_id:
            return None
        data["cinema_id"] = str(cinema_id)
        if not data.get("created_at"):
            data["created_at"] = datetime.now(timezone.utc)
        return CinemaResponse.model_validate(data)

    async def _get_cinemas_for_city(self, city_id: str) -> list[CinemaResponse]:
        docs = await self.db.cinemas.find({"city_id": city_id}).to_list(length=500)
        cinemas = [
            parsed
            for doc in docs
            if (parsed := self._parse_cinema(doc)) is not None
        ]
        if cinemas or self.http_client is None:
            return cinemas

        try:
            resp = await self.http_client.get(
                f"{self.settings.cinema_service_url.rstrip('/')}/api/v1/cinemas",
                params={"city_id": city_id},
            )
            if resp.is_success:
                payload = resp.json()
                if isinstance(payload, list):
                    return [
                        parsed
                        for item in payload
                        if isinstance(item, dict)
                        and (parsed := self._parse_cinema(item)) is not None
                    ]
        except httpx.RequestError:
            pass
        return []

    @staticmethod
    def _assert_can_manage_show(
        cinema_id: str,
        user_role: str | None,
        allowed_cinema_ids: list[str] | None,
    ) -> None:
        if user_role is None:
            return
        role = user_role.upper()
        if role == "ADMIN":
            return
        if role == "CINEMA":
            owned = set(allowed_cinema_ids or [])
            if not owned or cinema_id in owned:
                return
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Cinema role is not assigned to cinema '{cinema_id}'",
            )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions to create shows",
        )

    async def list_shows(
        self, movie_id: str, date_str: str, city_id: str
    ) -> list[ShowResponse]:
        cache_key = f"catalog:shows:{city_id}:{movie_id}:{date_str}"
        cached = await cache_get_json(cache_key)
        if cached is not None:
            return [ShowResponse.model_validate(item) for item in cached]

        cinema_objects = await self._get_cinemas_for_city(city_id)
        cinemas_by_id = {cinema.cinema_id: cinema for cinema in cinema_objects}
        cinema_ids = list(cinemas_by_id.keys())
        if not cinema_ids:
            return []

        day_start = datetime.fromisoformat(f"{date_str}T00:00:00+00:00")
        day_end = datetime.fromisoformat(f"{date_str}T23:59:59.999999+00:00")

        cursor = self.db.shows.find(
            {
                "movie_id": movie_id,
                "cinema_id": {"$in": cinema_ids},
                "start_time": {"$gte": day_start, "$lte": day_end},
            }
        ).sort("start_time", 1)

        docs = await cursor.to_list(length=500)
        result = [
            ShowResponse(
                id=str(doc["_id"]),
                movie_id=doc["movie_id"],
                cinema=cinemas_by_id.get(str(doc["cinema_id"])),
                hall_id=doc["hall_id"],
                start_time=doc["start_time"],
                end_time=doc["end_time"],
                language=doc["language"],
                format=doc["format"],
                pricing=doc["pricing"],
            )
            for doc in docs
        ]
        await cache_set_json(
            cache_key,
            [item.model_dump(mode="json") for item in result],
            self.settings.catalog_cache_ttl_seconds,
        )
        return result

    async def create_show(
        self,
        payload: CreateShowRequest,
        user_role: str | None = None,
        allowed_cinema_ids: list[str] | None = None,
    ) -> CreateShowResponse:
        self._assert_can_manage_show(payload.cinema_id, user_role, allowed_cinema_ids)
        doc = payload.model_dump()
        doc["_id"] = doc.pop("id")
        await self.db.shows.insert_one(doc)
        await cache_delete_pattern("catalog:shows:*")
        await cache_delete_pattern("catalog:movies:*")
        return CreateShowResponse(
            id=str(doc["_id"]),
            movie_id=doc["movie_id"],
            cinema_id=doc["cinema_id"],
            hall_id=doc["hall_id"],
            start_time=doc["start_time"],
            end_time=doc["end_time"],
            language=doc["language"],
            format=doc["format"],
            pricing=doc["pricing"],
        )