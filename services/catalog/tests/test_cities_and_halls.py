import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_get_cities_populates_and_reads_cache(
    client: AsyncClient, fake_db, cache_store: dict
) -> None:
    fake_db.cities.docs = [
        {"_id": "city_blr", "name": "Bengaluru", "state": "Karnataka", "country": "India"},
        {"_id": "city_hyd", "name": "Hyderabad", "state": "Telangana", "country": "India"},
    ]

    first = await client.get("/api/v1/catalog/cities")
    assert first.status_code == 200
    assert [c["id"] for c in first.json()] == ["city_blr", "city_hyd"]
    assert "catalog:cities" in cache_store

    # Mutate underlying DB; second call should still return cached result
    fake_db.cities.docs.clear()
    second = await client.get("/api/v1/catalog/cities")
    assert second.status_code == 200
    assert len(second.json()) == 2


@pytest.mark.asyncio
async def test_get_hall_layout_found_and_not_found(
    client: AsyncClient, fake_db
) -> None:
    missing = await client.get("/api/v1/catalog/halls/hall_missing/layout")
    assert missing.status_code == 404

    fake_db.halls.docs = [
        {
            "_id": "hall_audi_2",
            "cinema_id": "cin_pvr_01",
            "name": "Audi 2 (IMAX)",
            "total_seats": 120,
            "layout": {
                "rows": [
                    {
                        "row_label": "A",
                        "tier": "RECLINER",
                        "seats": [
                            {"seat_number": 1, "type": "STANDARD"},
                            {"seat_number": 2, "type": "STANDARD"},
                            {"type": "AISLE"},
                        ],
                    }
                ]
            },
        }
    ]

    found = await client.get("/api/v1/catalog/halls/hall_audi_2/layout")
    assert found.status_code == 200
    body = found.json()
    assert body["hall_id"] == "hall_audi_2"
    assert body["total_seats"] == 120
    assert body["layout"]["rows"][0]["row_label"] == "A"