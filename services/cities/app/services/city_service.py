from datetime import datetime, timezone
from typing import Any
from uuid import uuid4
from fastapi import HTTPException, status
from motor.motor_asyncio import AsyncIOMotorDatabase
from pymongo.errors import DuplicateKeyError
from app.models.schemas import CityResponse, CreateCityRequest, UpdateCityRequest


class CityService:
    def __init__(self, db: AsyncIOMotorDatabase) -> None:
        self.db = db

    @staticmethod
    def _to_city_response(doc: dict[str, Any]) -> CityResponse:
        return CityResponse(
            id=str(doc.get("_id") or doc.get("city_id") or doc["id"]),
            name=str(doc["name"]),
            state=str(doc["state"]),
            country=str(doc.get("country") or "India"),
        )

    @staticmethod
    def _assert_admin(user_role: str | None) -> None:
        if (user_role or "").upper() != "ADMIN":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only ADMIN users can manage cities",
            )

    async def list_cities(self) -> list[CityResponse]:
        docs = await self.db.cities.find().sort("name", 1).to_list(length=200)
        return [self._to_city_response(doc) for doc in docs]

    async def get_city(self, city_id: str) -> CityResponse:
        doc = await self.db.cities.find_one({"_id": city_id})
        if not doc:
            doc = await self.db.cities.find_one({"city_id": city_id})
        if not doc:
            doc = await self.db.cities.find_one({"id": city_id})
        if not doc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="City not found")
        return self._to_city_response(doc)

    async def create_city(
        self,
        payload: CreateCityRequest,
        user_role: str | None,
    ) -> CityResponse:
        self._assert_admin(user_role)
        city_id = payload.id or f"city_{uuid4().hex[:8]}"
        doc: dict[str, Any] = {
            "_id": city_id,
            "name": payload.name.strip(),
            "state": payload.state.strip(),
            "country": payload.country.strip(),
            "created_at": datetime.now(timezone.utc),
        }
        try:
            await self.db.cities.insert_one(doc)
        except DuplicateKeyError as exc:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"City with id '{city_id}' already exists",
            ) from exc
        return self._to_city_response(doc)

    async def update_city(
        self,
        city_id: str,
        payload: UpdateCityRequest,
        user_role: str | None,
    ) -> CityResponse:
        self._assert_admin(user_role)
        existing = await self.db.cities.find_one({"_id": city_id})
        if not existing:
            existing = await self.db.cities.find_one({"city_id": city_id})
        if not existing:
            existing = await self.db.cities.find_one({"id": city_id})
        if not existing:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="City not found")

        updates = payload.model_dump(exclude_unset=True, exclude_none=True)
        updates = {key: value.strip() for key, value in updates.items()}
        if updates:
            selector = {"_id": existing["_id"]} if "_id" in existing else {"id": city_id}
            await self.db.cities.update_one(selector, {"$set": updates})

        updated = await self.db.cities.find_one(selector if updates else {"_id": city_id})
        if not updated:
            updated = existing
        return self._to_city_response(updated)

    async def delete_city(self, city_id: str, user_role: str | None) -> None:
        self._assert_admin(user_role)
        result = await self.db.cities.delete_one({"_id": city_id})
        if result.deleted_count == 0:
            result = await self.db.cities.delete_one({"city_id": city_id})
        if result.deleted_count == 0:
            result = await self.db.cities.delete_one({"id": city_id})
        if result.deleted_count == 0:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="City not found")
