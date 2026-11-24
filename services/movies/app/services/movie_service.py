from datetime import datetime, timezone
import re
from typing import Any
from uuid import uuid4
from fastapi import HTTPException, status
from motor.motor_asyncio import AsyncIOMotorDatabase
from pymongo.errors import DuplicateKeyError
from app.models.schemas import (
    MovieCreate,
    MovieResponse,
    MovieUpdate,
)


class MovieService:
    def __init__(self, db: AsyncIOMotorDatabase) -> None:
        self.db = db

    @staticmethod
    def _to_movie_response(doc: dict[str, Any]) -> MovieResponse:
        return MovieResponse(
            id=str(doc.get("_id") or doc.get("id") or doc["movie_id"]),
            title=str(doc["title"]),
            duration_minutes=int(doc["duration_minutes"]),
            rating=doc.get("rating", "UA"),
            languages=doc.get("languages") or ["English"],
            formats=doc.get("formats") or ["2D"],
            synopsis=doc.get("synopsis"),
            city_ids=list(doc.get("city_ids") or []),
            release_date=doc.get("release_date"),
            poster_url=doc.get("poster_url"),
            is_active=bool(doc.get("is_active", True)),
        )

    @staticmethod
    def _assert_admin(user_role: str | None) -> None:
        if (user_role or "").upper() != "ADMIN":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only ADMIN users can manage movies",
            )

    async def list_movies(
        self,
        city_id: str | None = None,
        language: str | None = None,
        movie_format: str | None = None,
        active_only: bool = True,
    ) -> list[MovieResponse]:
        query: dict[str, Any] = {}
        if active_only:
            query["is_active"] = {"$ne": False}
        if city_id:
            query["$or"] = [
                {"city_ids": {"$exists": False}},
                {"city_ids": []},
                {"city_ids": city_id},
            ]
        if language:
            query["languages"] = {
                "$elemMatch": {"$regex": re.escape(language.strip()), "$options": "i"}
            }
        if movie_format:
            query["formats"] = {
                "$elemMatch": {"$regex": re.escape(movie_format.strip()), "$options": "i"}
            }

        docs = await self.db.movies.find(query).sort("title", 1).to_list(length=200)
        return [self._to_movie_response(doc) for doc in docs]

    async def get_movie(self, movie_id: str) -> MovieResponse:
        doc = await self.db.movies.find_one({"_id": movie_id})
        if not doc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Movie not found")
        return self._to_movie_response(doc)

    async def create_movie(self, payload: MovieCreate, user_role: str | None) -> MovieResponse:
        self._assert_admin(user_role)
        movie_id = payload.id or f"mov_{uuid4().hex[:10]}"
        doc: dict[str, Any] = {
            "_id": movie_id,
            **payload.model_dump(mode="json", exclude={"id"}),
            "created_at": datetime.now(timezone.utc),
        }
        try:
            await self.db.movies.insert_one(doc)
        except DuplicateKeyError as exc:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Movie with id '{movie_id}' already exists",
            ) from exc
        return self._to_movie_response(doc)

    async def update_movie(
        self,
        movie_id: str,
        payload: MovieUpdate,
        user_role: str | None,
    ) -> MovieResponse:
        self._assert_admin(user_role)
        existing = await self.db.movies.find_one({"_id": movie_id})
        if not existing:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Movie not found")

        updates = payload.model_dump(mode="json", exclude_unset=True, exclude_none=True)
        if updates:
            await self.db.movies.update_one({"_id": movie_id}, {"$set": updates})

        updated = await self.db.movies.find_one({"_id": movie_id})
        if not updated:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Movie not found")
        return self._to_movie_response(updated)

    async def delete_movie(self, movie_id: str, user_role: str | None) -> None:
        self._assert_admin(user_role)
        result = await self.db.movies.delete_one({"_id": movie_id})
        if result.deleted_count == 0:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Movie not found")
