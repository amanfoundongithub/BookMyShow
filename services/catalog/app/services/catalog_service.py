from datetime import datetime, timezone
from fastapi import HTTPException, status
import httpx
from motor.motor_asyncio import AsyncIOMotorDatabase
from app.core.cache import cache_delete_pattern, cache_get_json, cache_set_json
from app.core.config import get_settings
from app.models.schemas import (
    CityResponse,
    CreateShowRequest,
    MovieResponse,
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

    async def _get_cinema_ids_for_city(self, city_id: str) -> list[str]:
        docs = await self.db.cinemas.find(
            {"city_id": city_id}, {"_id": 1, "cinema_id": 1}
        ).to_list(length=500)
        ids = [
            str(doc.get("cinema_id") or doc.get("_id"))
            for doc in docs
            if doc.get("cinema_id") or doc.get("_id")
        ]
        if ids or self.http_client is None:
            return ids

        try:
            resp = await self.http_client.get(
                f"{self.settings.cinema_service_url.rstrip('/')}/api/v1/cinemas",
                params={"city_id": city_id},
            )
            if resp.is_success:
                payload = resp.json()
                return [
                    str(item["cinema_id"])
                    for item in payload
                    if isinstance(item, dict) and item.get("cinema_id")
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

    async def list_cities(self) -> list[CityResponse]:
        cache_key = "catalog:cities"
        cached = await cache_get_json(cache_key)
        if cached is not None:
            return [CityResponse.model_validate(item) for item in cached]

        docs = await self.db.cities.find().sort("name", 1).to_list(length=200)
        result = [
            CityResponse(
                id=doc["_id"],
                name=doc["name"],
                state=doc["state"],
                country=doc.get("country", "India"),
            )
            for doc in docs
        ]
        await cache_set_json(
            cache_key,
            [item.model_dump() for item in result],
            self.settings.catalog_cache_ttl_seconds,
        )
        return result

    async def list_movies_by_city(self, city_id: str) -> list[MovieResponse]:
        cache_key = f"catalog:movies:city:{city_id}"
        cached = await cache_get_json(cache_key)
        if cached is not None:
            return [MovieResponse.model_validate(item) for item in cached]

        cinema_ids = await self._get_cinema_ids_for_city(city_id)
        if not cinema_ids:
            return []

        now = datetime.now(timezone.utc)
        movie_ids = await self.db.shows.distinct(
            "movie_id",
            {"cinema_id": {"$in": cinema_ids}, "start_time": {"$gte": now}},
        )
        docs = await self.db.movies.find({"_id": {"$in": movie_ids}}).to_list(length=200)
        result = [
            MovieResponse(
                id=doc["_id"],
                title=doc["title"],
                duration_minutes=doc["duration_minutes"],
                rating=doc["rating"],
                languages=doc.get("languages", []),
                formats=doc.get("formats", []),
            )
            for doc in docs
        ]
        await cache_set_json(
            cache_key,
            [item.model_dump() for item in result],
            self.settings.catalog_cache_ttl_seconds,
        )
        return result

    async def list_shows(
        self, movie_id: str, date_str: str, city_id: str
    ) -> list[ShowResponse]:
        cache_key = f"catalog:shows:{city_id}:{movie_id}:{date_str}"
        cached = await cache_get_json(cache_key)
        if cached is not None:
            return [ShowResponse.model_validate(item) for item in cached]

        cinema_ids = await self._get_cinema_ids_for_city(city_id)
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
                id=doc["_id"],
                movie_id=doc["movie_id"],
                cinema_id=doc["cinema_id"],
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
    ) -> ShowResponse:
        self._assert_can_manage_show(payload.cinema_id, user_role, allowed_cinema_ids)
        doc = payload.model_dump()
        doc["_id"] = doc.pop("id")
        await self.db.shows.insert_one(doc)
        await cache_delete_pattern("catalog:shows:*")
        await cache_delete_pattern("catalog:movies:*")
        return ShowResponse(
            id=doc["_id"],
            movie_id=doc["movie_id"],
            cinema_id=doc["cinema_id"],
            hall_id=doc["hall_id"],
            start_time=doc["start_time"],
            end_time=doc["end_time"],
            language=doc["language"],
            format=doc["format"],
            pricing=doc["pricing"],
        )