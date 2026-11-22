from datetime import datetime, timezone
from typing import Any
from uuid import uuid4
from fastapi import HTTPException, status
from motor.motor_asyncio import AsyncIOMotorDatabase
from app.models.schemas import (
    CinemaResponse,
    CreateCinemaRequest,
    UpdateCinemaRequest,
)


class CinemaService:
    def __init__(self, db: AsyncIOMotorDatabase) -> None:
        self.db = db

    @staticmethod
    def _to_cinema_response(doc: dict[str, Any]) -> CinemaResponse:
        return CinemaResponse(
            cinema_id=str(doc["cinema_id"]),
            name=str(doc["name"]),
            city_id=str(doc["city_id"]),
            state=doc.get("state"),
            address=str(doc["address"]),
            amenities=list(doc.get("amenities") or []),
            is_active=bool(doc.get("is_active", True)),
            created_at=doc["created_at"],
        )

    @staticmethod
    def _assert_can_manage_cinema(
        cinema_id: str,
        user_role: str | None,
        allowed_cinema_ids: list[str] | None,
    ) -> None:
        role = (user_role or "USER").upper()
        if role == "ADMIN":
            return
        if role == "CINEMA":
            owned = set(allowed_cinema_ids or [])
            if cinema_id in owned:
                return
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Cinema role is not assigned to cinema '{cinema_id}'",
            )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions to manage cinemas",
        )

    async def list_cinemas(
        self,
        city_id: str | None = None,
        include_inactive: bool = False,
    ) -> list[CinemaResponse]:
        query: dict[str, Any] = {} if include_inactive else {"is_active": {"$ne": False}}
        if city_id:
            query["city_id"] = city_id
        docs = await self.db.cinemas.find(query, {"_id": 0}).sort("name", 1).to_list(length=200)
        return [self._to_cinema_response(doc) for doc in docs]

    async def get_cinema(self, cinema_id: str) -> CinemaResponse:
        doc = await self.db.cinemas.find_one({"cinema_id": cinema_id}, {"_id": 0})
        if not doc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cinema not found")
        return self._to_cinema_response(doc)

    async def create_cinema(
        self,
        payload: CreateCinemaRequest,
        user_role: str | None,
        allowed_cinema_ids: list[str] | None = None,
    ) -> CinemaResponse:
        role = (user_role or "USER").upper()
        if role not in {"ADMIN", "CINEMA"}:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only ADMIN or CINEMA roles can create cinemas",
            )

        city_doc = await self.db.cities.find_one({"id": payload.city_id})
        if not city_doc:
            city_doc = await self.db.cities.find_one({"city_id": payload.city_id})
        resolved_state: str | None = payload.state or (
            str(city_doc["state"]) if city_doc and city_doc.get("state") else None
        )

        cinema_id = f"cin_{uuid4().hex[:8]}"
        now = datetime.now(timezone.utc)
        doc: dict[str, Any] = {
            "cinema_id": cinema_id,
            "name": payload.name.strip(),
            "city_id": payload.city_id.strip(),
            "state": resolved_state,
            "address": payload.address.strip(),
            "amenities": payload.amenities,
            "is_active": True,
            "created_at": now,
        }
        await self.db.cinemas.insert_one(doc)
        return self._to_cinema_response(doc)

    async def update_cinema(
        self,
        cinema_id: str,
        payload: UpdateCinemaRequest,
        user_role: str | None,
        allowed_cinema_ids: list[str] | None = None,
    ) -> CinemaResponse:
        self._assert_can_manage_cinema(cinema_id, user_role, allowed_cinema_ids)
        existing = await self.db.cinemas.find_one({"cinema_id": cinema_id})
        if not existing:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cinema not found")

        updates: dict[str, Any] = payload.model_dump(exclude_none=True)
        if not updates:
            return self._to_cinema_response(existing)

        await self.db.cinemas.update_one({"cinema_id": cinema_id}, {"$set": updates})
        updated = await self.db.cinemas.find_one({"cinema_id": cinema_id}, {"_id": 0})
        if not updated:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cinema not found")
        return self._to_cinema_response(updated)