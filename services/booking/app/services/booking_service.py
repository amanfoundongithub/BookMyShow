from datetime import datetime, timedelta, timezone
from decimal import Decimal
from uuid import uuid4
import httpx
from motor.motor_asyncio import AsyncIOMotorDatabase
from app.core.config import get_settings
from app.core.mq import publish_booking_event
from app.models.booking import BookingStatus
from app.models.schemas import (
    BookingSummaryResponse,
    HoldSeatsRequest,
    HoldSeatsResponse,
    ReleaseBookingRequest,
    ReleaseBookingResponse,
    SeatMapResponse,
)
from app.redis_lock import SeatLockManager
from app.ws_manager import ShowWsManager


class SeatConflictError(Exception):
    def __init__(self, seat_id: str, reason: str) -> None:
        self.seat_id = seat_id
        self.reason = reason
        super().__init__(f"Seat {seat_id} unavailable ({reason})")


class BookingNotFoundError(Exception):
    pass


class InvalidBookingStateError(Exception):
    pass


class BookingService:
    def __init__(
        self,
        db: AsyncIOMotorDatabase,
        lock_manager: SeatLockManager,
        ws_manager: ShowWsManager,
        http_client: httpx.AsyncClient | None = None,
    ) -> None:
        self.db = db
        self.lock_manager = lock_manager
        self.ws_manager = ws_manager
        self.http_client = http_client
        self.settings = get_settings()

    @staticmethod
    def _extract_seat_ids(layout_payload: dict) -> list[str]:
        seat_ids: list[str] = []
        for row in layout_payload.get("layout", {}).get("rows", []):
            row_label = row["row_label"]
            for seat in row.get("seats", []):
                if seat.get("type") != "AISLE" and seat.get("seat_number") is not None:
                    seat_ids.append(f"{row_label}{seat['seat_number']}")
        return seat_ids

    async def list_user_bookings(
        self, user_id: str, limit: int = 50
    ) -> list[BookingSummaryResponse]:
        cursor = (
            self.db.bookings.find({"user_id": user_id})
            .sort("created_at", -1)
            .limit(limit)
        )
        docs = await cursor.to_list(length=limit)
        return [
            BookingSummaryResponse(
                booking_id=doc.get("booking_id") or str(doc["_id"]),
                show_id=doc["show_id"],
                hall_id=doc.get("hall_id"),
                user_id=doc["user_id"],
                seats=doc.get("seats", []),
                tier=doc.get("tier"),
                total_amount=Decimal(str(doc.get("total_amount", "0.00"))),
                currency=doc.get("currency", "INR"),
                status=BookingStatus(doc["status"]),
                hold_expires_at=doc.get("hold_expires_at"),
                created_at=doc.get("created_at"),
            )
            for doc in docs
        ]

    async def get_seat_map(self, show_id: str, hall_id: str) -> SeatMapResponse:
        layout_data: dict = {"hall_id": hall_id, "layout": {"rows": []}}
        if self.http_client is not None:
            hall_url = f"{self.settings.hall_service_url.rstrip('/')}/api/v1/halls/{hall_id}/layout"
            try:
                resp = await self.http_client.get(hall_url)
                resp.raise_for_status()
                layout_data = resp.json()
            except httpx.HTTPError:
                fallback_url = (
                    f"{self.settings.catalog_service_url.rstrip('/')}/api/v1/catalog/halls/{hall_id}/layout"
                )
                resp = await self.http_client.get(fallback_url)
                resp.raise_for_status()
                layout_data = resp.json()

        seat_ids = self._extract_seat_ids(layout_data)
        states = await self.lock_manager.get_show_seat_states(show_id, seat_ids)
        return SeatMapResponse(show_id=show_id, hall_id=hall_id, seats=states)

    async def hold_seats(
        self, payload: HoldSeatsRequest, tier_price: Decimal, correlation_id: str | None = None
    ) -> HoldSeatsResponse:
        booking_id = f"BK_{uuid4().hex[:8].upper()}"
        acquired, conflict_seat, reason = await self.lock_manager.acquire_seats(
            show_id=payload.show_id,
            seat_ids=payload.seats,
            booking_id=booking_id,
        )
        if not acquired:
            raise SeatConflictError(
                seat_id=conflict_seat or "", reason=reason or "LOCKED"
            )

        now = datetime.now(timezone.utc)
        expires_at = now + timedelta(seconds=self.settings.seat_hold_ttl_seconds)
        total_amount = (tier_price * Decimal(len(payload.seats))).quantize(Decimal("0.01"))

        doc = {
            "_id": booking_id,
            "user_id": payload.user_id,
            "show_id": payload.show_id,
            "seats": payload.seats,
            "tier": payload.tier,
            "total_amount": float(total_amount),
            "currency": "INR",
            "status": BookingStatus.HELD.value,
            "hold_expires_at": expires_at,
            "payment_id": None,
            "created_at": now,
        }
        try:
            await self.db.bookings.insert_one(doc)
        except Exception:
            await self.lock_manager.release_seats(payload.show_id, payload.seats, booking_id)
            raise

        await self.ws_manager.publish_seat_update(
            show_id=payload.show_id,
            seats=payload.seats,
            status=BookingStatus.HELD.value,
            booking_id=booking_id,
        )
        await publish_booking_event(
            "booking.created",
            {
                "event_type": "booking.created",
                "correlation_id": correlation_id,
                "booking_id": booking_id,
                "user_id": payload.user_id,
                "show_id": payload.show_id,
                "seats": payload.seats,
                "tier": payload.tier,
                "total_amount": str(total_amount),
                "currency": "INR",
                "hold_expires_at": expires_at.isoformat(),
            },
        )

        return HoldSeatsResponse(
            booking_id=booking_id,
            show_id=payload.show_id,
            user_id=payload.user_id,
            seats=payload.seats,
            tier=payload.tier,
            total_amount=total_amount,
            currency="INR",
            status=BookingStatus.HELD,
            hold_expires_at=expires_at,
        )

    async def release_booking(
        self, payload: ReleaseBookingRequest
    ) -> ReleaseBookingResponse:
        booking = await self.db.bookings.find_one({"_id": payload.booking_id})
        if not booking:
            raise BookingNotFoundError(f"Booking {payload.booking_id} not found")
        if booking.get("user_id") != payload.user_id:
            raise InvalidBookingStateError("Booking belongs to another user")
        if booking.get("status") != BookingStatus.HELD.value:
            raise InvalidBookingStateError(
                f"Cannot release booking in state {booking.get('status')}"
            )

        await self.lock_manager.release_seats(
            show_id=booking["show_id"],
            seat_ids=booking["seats"],
            booking_id=booking["_id"],
        )
        await self.db.bookings.update_one(
            {"_id": booking["_id"]},
            {"$set": {"status": BookingStatus.CANCELLED.value}},
        )
        await self.ws_manager.publish_seat_update(
            show_id=booking["show_id"],
            seats=booking["seats"],
            status="AVAILABLE",
            booking_id=booking["_id"],
        )
        return ReleaseBookingResponse(
            booking_id=booking["_id"],
            status=BookingStatus.CANCELLED,
            released_seats=booking["seats"],
        )