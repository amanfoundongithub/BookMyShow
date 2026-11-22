import logging
from motor.motor_asyncio import AsyncIOMotorDatabase
from app.models.booking import BookingStatus
from app.redis_lock import SeatLockManager
from app.ws_manager import ShowWsManager

logger = logging.getLogger(__name__)


class BookingEventHandler:
    def __init__(
        self,
        db: AsyncIOMotorDatabase,
        lock_manager: SeatLockManager,
        ws_manager: ShowWsManager,
    ) -> None:
        self.db = db
        self.lock_manager = lock_manager
        self.ws_manager = ws_manager

    async def handle_payment_event(self, routing_key: str, payload: dict) -> None:
        booking_id = payload.get("booking_id")
        if not booking_id:
            logger.warning("Payment event %s missing booking_id", routing_key)
            return

        booking = await self.db.bookings.find_one({"_id": booking_id})
        if not booking:
            logger.warning("Booking %s not found for event %s", booking_id, routing_key)
            return

        show_id = booking["show_id"]
        seats = booking["seats"]

        if routing_key == "payment.completed":
            ok, reason = await self.lock_manager.confirm_seats(show_id, seats, booking_id)
            if not ok:
                logger.error(
                    "Seat confirmation failed for booking %s: %s", booking_id, reason
                )
                return
            await self.db.bookings.update_one(
                {"_id": booking_id},
                {
                    "$set": {
                        "status": BookingStatus.CONFIRMED.value,
                        "payment_id": payload.get("payment_id"),
                    }
                },
            )
            await self.ws_manager.publish_seat_update(
                show_id=show_id,
                seats=seats,
                status=BookingStatus.CONFIRMED.value,
                booking_id=booking_id,
            )

        elif routing_key == "payment.failed":
            await self.lock_manager.release_seats(show_id, seats, booking_id)
            await self.db.bookings.update_one(
                {"_id": booking_id},
                {
                    "$set": {
                        "status": BookingStatus.CANCELLED.value,
                        "payment_id": payload.get("payment_id"),
                    }
                },
            )
            await self.ws_manager.publish_seat_update(
                show_id=show_id,
                seats=seats,
                status="AVAILABLE",
                booking_id=booking_id,
            )