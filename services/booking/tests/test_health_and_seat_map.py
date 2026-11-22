from unittest.mock import MagicMock
import pytest
from httpx import AsyncClient
from app.tests.conftest import FakeRedis


@pytest.mark.asyncio
async def test_health_and_ready(client: tuple[AsyncClient, object]) -> None:
    ac, _ = client
    h = await ac.get("/health")
    assert h.status_code == 200
    assert h.json() == {"status": "ok", "service": "booking-service"}

    r = await ac.get("/ready")
    assert r.status_code == 200
    assert r.json() == {"status": "ready"}


@pytest.mark.asyncio
async def test_seat_map_combines_layout_locks_and_confirmed(
    client: tuple[AsyncClient, object], fake_redis: FakeRedis
) -> None:
    ac, mock_http = client
    mock_resp = MagicMock()
    mock_resp.raise_for_status = MagicMock()
    mock_resp.json.return_value = {
        "hall_id": "hall_audi_2",
        "layout": {
            "rows": [
                {
                    "row_label": "A",
                    "tier": "RECLINER",
                    "seats": [
                        {"seat_number": 1, "type": "STANDARD"},
                        {"seat_number": 2, "type": "STANDARD"},
                        {"type": "AISLE"},
                        {"seat_number": 3, "type": "STANDARD"},
                    ],
                }
            ]
        },
    }
    mock_http.get.return_value = mock_resp

    fake_redis.sets["occupied:show:show_1"].add("A1")
    fake_redis.kv["lock:show:show_1:seat:A2"] = "BK_OTHER"

    resp = await ac.get(
        "/api/v1/bookings/shows/show_1/seat-map", params={"hall_id": "hall_audi_2"}
    )
    assert resp.status_code == 200
    assert resp.json()["seats"] == {
        "A1": "CONFIRMED",
        "A2": "HELD",
        "A3": "AVAILABLE",
    }