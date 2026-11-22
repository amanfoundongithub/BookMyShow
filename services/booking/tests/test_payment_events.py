import pytest
from app.services.event_handler import BookingEventHandler
from app.redis_lock import SeatLockManager
from app.ws_manager import ShowWsManager
from app.tests.conftest import FakeBookingDatabase, FakeRedis


@pytest.mark.asyncio
async def test_payment_completed_confirms_booking_and_occupies_seats(
    fake_db: FakeBookingDatabase, fake_redis: FakeRedis
) -> None:
    lock_manager = SeatLockManager(redis=fake_redis, ttl_seconds=600)  # type: ignore[arg-type]
    ws_manager = ShowWsManager(redis=fake_redis)  # type: ignore[arg-type]
    handler = BookingEventHandler(
        db=fake_db, lock_manager=lock_manager, ws_manager=ws_manager  # type: ignore[arg-type]
    )

    booking_id = "BK_TEST_1"
    await lock_manager.acquire_seats("show_991823", ["A1", "A2"], booking_id)
    await fake_db.bookings.insert_one(
        {
            "_id": booking_id,
            "user_id": "usr_1",
            "show_id": "show_991823",
            "seats": ["A1", "A2"],
            "status": "HELD",
        }
    )

    await handler.handle_payment_event(
        "payment.completed",
        {"booking_id": booking_id, "payment_id": "txn_123"},
    )

    assert fake_db.bookings.docs[booking_id]["status"] == "CONFIRMED"
    assert fake_db.bookings.docs[booking_id]["payment_id"] == "txn_123"
    assert "lock:show:show_991823:seat:A1" not in fake_redis.kv
    assert fake_redis.sets["occupied:show:show_991823"] == {"A1", "A2"}


@pytest.mark.asyncio
async def test_payment_failed_cancels_booking_and_releases_locks(
    fake_db: FakeBookingDatabase, fake_redis: FakeRedis
) -> None:
    lock_manager = SeatLockManager(redis=fake_redis, ttl_seconds=600)  # type: ignore[arg-type]
    ws_manager = ShowWsManager(redis=fake_redis)  # type: ignore[arg-type]
    handler = BookingEventHandler(
        db=fake_db, lock_manager=lock_manager, ws_manager=ws_manager  # type: ignore[arg-type]
    )

    booking_id = "BK_TEST_2"
    await lock_manager.acquire_seats("show_991823", ["A1"], booking_id)
    await fake_db.bookings.insert_one(
        {
            "_id": booking_id,
            "user_id": "usr_1",
            "show_id": "show_991823",
            "seats": ["A1"],
            "status": "HELD",
        }
    )

    await handler.handle_payment_event(
        "payment.failed",
        {"booking_id": booking_id, "payment_id": "txn_456"},
    )

    assert fake_db.bookings.docs[booking_id]["status"] == "CANCELLED"
    assert "lock:show:show_991823:seat:A1" not in fake_redis.kv