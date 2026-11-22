from datetime import datetime, timezone
from motor.motor_asyncio import AsyncIOMotorDatabase
from app.core.cache import cache_delete_pattern, cache_get_json, cache_set_json
from app.core.config import get_settings
from app.models.schemas import (
    CityResponse,
    CreateShowRequest,
    HallLayoutResponse,
    MovieResponse,
    ShowResponse,
)


class CatalogService:
    def __init__(self, db: AsyncIOMotorDatabase) -> None:
        self.db = db
        self.settings = get_settings()

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
        
        cinema_ids = await self.db.cinemas.distinct("_id", {"city_id": city_id})

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

        cinema_ids = await self.db.cinemas.distinct("_id", {"city_id": city_id})
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

    async def get_hall_layout(self, hall_id: str) -> HallLayoutResponse | None:
        cache_key = f"catalog:hall:{hall_id}:layout"
        cached = await cache_get_json(cache_key)
        if cached is not None:
            return HallLayoutResponse.model_validate(cached)

        doc = await self.db.halls.find_one({"_id": hall_id})
        if not doc:
            return None

        result = HallLayoutResponse(
            hall_id=doc["_id"],
            cinema_id=doc["cinema_id"],
            name=doc["name"],
            total_seats=doc["total_seats"],
            layout=doc["layout"],
        )
        await cache_set_json(
            cache_key,
            result.model_dump(),
            self.settings.catalog_cache_ttl_seconds,
        )
        return result

    async def create_show(self, payload: CreateShowRequest) -> ShowResponse:
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