import pytest
from httpx import AsyncClient
from app.tests.conftest import FakeBookingDatabase, FakeRedis


@pytest.mark.asyncio
async def test_hold_seats_success_and_atomic_conflict_rollback(
    client: tuple[AsyncClient, object],
    fake_db: FakeBookingDatabase,
    fake_redis: FakeRedis,
    published_mq_events: list,
) -> None:
    ac, _ = client

    # User A holds A1 and A2
    r1 = await ac.post(
        "/api/v1/bookings/hold",
        params={"tier_price": "450.00"},
        json={
            "show_id": "show_991823",
            "user_id": "usr_a",
            "seats": ["A1", "A2"],
            "tier": "RECLINER",
        },
    )
    assert r1.status_code == 201
    b1 = r1.json()
    assert b1["status"] == "HELD"
    assert float(b1["total_amount"]) == 900.00
    assert len(published_mq_events) == 1
    assert published_mq_events[0][0] == "booking.created"

    # User B tries to grab A2 and A3 -> must fail atomically and NOT lock A3
    r2 = await ac.post(
        "/api/v1/bookings/hold",
        params={"tier_price": "450.00"},
        json={
            "show_id": "show_991823",
            "user_id": "usr_b",
            "seats": ["A2", "A3"],
            "tier": "RECLINER",
        },
    )
    assert r2.status_code == 409
    assert "A2" in r2.json()["detail"]
    assert "lock:show:show_991823:seat:A3" not in fake_redis.kv
    assert len(fake_db.bookings.docs) == 1


@pytest.mark.asyncio
async def test_release_booking_frees_locks_and_marks_cancelled(
    client: tuple[AsyncClient, object],
    fake_db: FakeBookingDatabase,
    fake_redis: FakeRedis,
) -> None:
    ac, _ = client

    create_resp = await ac.post(
        "/api/v1/bookings/hold",
        json={
            "show_id": "show_991823",
            "user_id": "usr_a",
            "seats": ["A1"],
            "tier": "RECLINER",
        },
    )
    assert create_resp.status_code == 201
    booking_id = create_resp.json()["booking_id"]
    assert "lock:show:show_991823:seat:A1" in fake_redis.kv

    rel_resp = await ac.post(
        "/api/v1/bookings/release",
        json={"booking_id": booking_id, "user_id": "usr_a"},
    )
    assert rel_resp.status_code == 200
    assert rel_resp.json()["status"] == "CANCELLED"
    assert "lock:show:show_991823:seat:A1" not in fake_redis.kv
    assert fake_db.bookings.docs[booking_id]["status"] == "CANCELLED"