from datetime import datetime, timedelta, timezone
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_get_movies_by_city_filters_upcoming_shows(
    client: AsyncClient, fake_db
) -> None:
    now = datetime.now(timezone.utc)
    fake_db.cinemas.docs = [
        {"_id": "cin_pvr_01", "city_id": "city_hyd", "name": "PVR ICON", "address": "Hyd"},
        {"_id": "cin_other", "city_id": "city_blr", "name": "Other", "address": "Blr"},
    ]
    fake_db.movies.docs = [
        {
            "_id": "mov_upcoming",
            "title": "Inception",
            "duration_minutes": 148,
            "rating": "UA",
            "languages": ["English"],
            "formats": ["IMAX 2D"],
        },
        {
            "_id": "mov_past",
            "title": "Old Film",
            "duration_minutes": 120,
            "rating": "UA",
            "languages": ["English"],
            "formats": ["2D"],
        },
    ]
    fake_db.shows.docs = [
        {
            "_id": "show_future",
            "movie_id": "mov_upcoming",
            "cinema_id": "cin_pvr_01",
            "hall_id": "hall_audi_2",
            "start_time": now + timedelta(hours=3),
            "end_time": now + timedelta(hours=5),
            "language": "English",
            "format": "IMAX 2D",
            "pricing": {"RECLINER": 450.0},
        },
        {
            "_id": "show_past",
            "movie_id": "mov_past",
            "cinema_id": "cin_pvr_01",
            "hall_id": "hall_audi_2",
            "start_time": now - timedelta(hours=5),
            "end_time": now - timedelta(hours=3),
            "language": "English",
            "format": "2D",
            "pricing": {"CLASSIC": 180.0},
        },
    ]

    resp = await client.get("/api/v1/catalog/movies", params={"city": "city_hyd"})
    assert resp.status_code == 200
    movies = resp.json()
    assert [m["id"] for m in movies] == ["mov_upcoming"]


@pytest.mark.asyncio
async def test_create_show_invalidates_shows_and_movies_cache(
    client: AsyncClient, fake_db, cache_store: dict
) -> None:
    cache_store["catalog:shows:city_hyd:mov_inception:2026-11-23"] = []
    cache_store["catalog:movies:city:city_hyd"] = []
    cache_store["catalog:cities"] = [{"id": "city_hyd", "name": "Hyderabad", "state": "Telangana", "country": "India"}]

    payload = {
        "id": "show_new_1",
        "movie_id": "mov_inception",
        "cinema_id": "cin_pvr_01",
        "hall_id": "hall_audi_2",
        "start_time": "2026-11-23T18:30:00Z",
        "end_time": "2026-11-23T21:00:00Z",
        "language": "English",
        "format": "IMAX 2D",
        "pricing": {"RECLINER": 450.0, "PRIME": 280.0, "CLASSIC": 180.0},
    }

    resp = await client.post("/api/v1/catalog/shows", json=payload)
    assert resp.status_code == 201
    assert resp.json()["id"] == "show_new_1"
    assert "catalog:shows:city_hyd:mov_inception:2026-11-23" not in cache_store
    assert "catalog:movies:city:city_hyd" not in cache_store
    assert "catalog:cities" in cache_store


@pytest.mark.asyncio
async def test_get_shows_date_validation(client: AsyncClient) -> None:
    bad = await client.get(
        "/api/v1/catalog/shows",
        params={"movie_id": "mov_inception", "date": "23-11-2026", "city": "city_hyd"},
    )
    assert bad.status_code == 422