from datetime import datetime, timezone
from typing import Any
from uuid import uuid4
from fastapi import HTTPException, status
import httpx
from motor.motor_asyncio import AsyncIOMotorDatabase
from app.core.config import get_settings
from app.models.schemas import (
    CreateHallRequest,
    HallLayout,
    HallResponse,
    UpdateHallLayoutRequest,
)


class HallService:
    def __init__(
        self,
        db: AsyncIOMotorDatabase,
        http_client: httpx.AsyncClient | None = None,
    ) -> None:
        self.db = db
        self.http_client = http_client
        self.settings = get_settings()

    @staticmethod
    def _count_sellable_seats(layout: HallLayout) -> int:
        count = 0
        for row in layout.rows:
            for seat in row.seats:
                if seat.type != "AISLE" and seat.seat_number is not None:
                    count += 1
        return count

    @staticmethod
    def _to_hall_response(doc: dict[str, Any]) -> HallResponse:
        raw_layout = doc.get("layout") or {"rows": []}
        layout = HallLayout(**raw_layout)
        return HallResponse(
            hall_id=str(doc["hall_id"]),
            cinema_id=str(doc["cinema_id"]),
            name=str(doc["name"]),
            screen_format=str(doc.get("screen_format", "2D")),
            total_seats=int(doc.get("total_seats", HallService._count_sellable_seats(layout))),
            layout=layout,
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
            detail="Insufficient permissions to manage halls",
        )

    async def _ensure_cinema_exists(self, cinema_id: str) -> None:
        # Check local Mongo collection first (in case shared DB), then Cinema Service
        local_cinema = await self.db.cinemas.find_one({"cinema_id": cinema_id})
        if local_cinema:
            return

        if self.http_client is not None:
            url = f"{self.settings.cinema_service_url.rstrip('/')}/api/v1/cinemas/{cinema_id}"
            try:
                resp = await self.http_client.get(url)
            except httpx.RequestError as exc:
                raise HTTPException(
                    status_code=status.HTTP_502_BAD_GATEWAY,
                    detail=f"Unable to verify cinema '{cinema_id}': {exc}",
                ) from exc

            if resp.status_code == status.HTTP_404_NOT_FOUND:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Cinema '{cinema_id}' not found",
                )
            resp.raise_for_status()

    async def list_halls(self, cinema_id: str | None = None) -> list[HallResponse]:
        query: dict[str, Any] = {}
        if cinema_id:
            query["cinema_id"] = cinema_id
        docs = await self.db.halls.find(query, {"_id": 0}).sort("name", 1).to_list(length=200)
        return [self._to_hall_response(doc) for doc in docs]

    async def get_hall(self, hall_id: str) -> HallResponse:
        doc = await self.db.halls.find_one({"hall_id": hall_id}, {"_id": 0})
        if not doc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Hall not found")
        return self._to_hall_response(doc)

    async def create_hall(
        self,
        payload: CreateHallRequest,
        user_role: str | None,
        allowed_cinema_ids: list[str] | None = None,
    ) -> HallResponse:
        self._assert_can_manage_cinema(payload.cinema_id, user_role, allowed_cinema_ids)
        await self._ensure_cinema_exists(payload.cinema_id)

        hall_id = f"hall_{uuid4().hex[:8]}"
        total_seats = self._count_sellable_seats(payload.layout)
        now = datetime.now(timezone.utc)
        doc: dict[str, Any] = {
            "hall_id": hall_id,
            "cinema_id": payload.cinema_id.strip(),
            "name": payload.name.strip(),
            "screen_format": payload.screen_format.strip(),
            "total_seats": total_seats,
            "layout": payload.layout.model_dump(),
            "created_at": now,
        }
        await self.db.halls.insert_one(doc)
        return self._to_hall_response(doc)

    async def update_hall_layout(
        self,
        hall_id: str,
        payload: UpdateHallLayoutRequest,
        user_role: str | None,
        allowed_cinema_ids: list[str] | None = None,
    ) -> HallResponse:
        existing = await self.db.halls.find_one({"hall_id": hall_id})
        if not existing:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Hall not found")

        cinema_id = str(existing["cinema_id"])
        self._assert_can_manage_cinema(cinema_id, user_role, allowed_cinema_ids)

        updates: dict[str, Any] = {
            "layout": payload.layout.model_dump(),
            "total_seats": self._count_sellable_seats(payload.layout),
        }
        if payload.name is not None:
            updates["name"] = payload.name.strip()
        if payload.screen_format is not None:
            updates["screen_format"] = payload.screen_format.strip()

        await self.db.halls.update_one({"hall_id": hall_id}, {"$set": updates})
        updated = await self.db.halls.find_one({"hall_id": hall_id}, {"_id": 0})
        if not updated:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Hall not found")
        return self._to_hall_response(updated)