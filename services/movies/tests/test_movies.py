from copy import deepcopy
import re
from typing import Any
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch
import pytest
import pytest_asyncio
from bson import BSON
from httpx import ASGITransport, AsyncClient
from pymongo.errors import DuplicateKeyError
from app.core.db import close_db, connect_db, get_database
from app.core.movie_options import DEFAULT_MOVIE_OPTIONS, MOVIE_OPTIONS_ID
from app.main import app


class FakeCursor:
    def __init__(self, docs: list[dict[str, Any]]) -> None:
        self.docs = docs

    def sort(self, field: str, direction: int) -> "FakeCursor":
        self.docs.sort(key=lambda doc: doc.get(field, ""), reverse=direction < 0)
        return self

    async def to_list(self, length: int) -> list[dict[str, Any]]:
        return self.docs[:length]


class FakeCollection:
    def __init__(self) -> None:
        self.docs: list[dict[str, Any]] = []

    def find(self, query: dict[str, Any]) -> FakeCursor:
        return FakeCursor([deepcopy(doc) for doc in self.docs if self._matches(doc, query)])

    async def find_one(self, query: dict[str, Any]) -> dict[str, Any] | None:
        return next(
            (deepcopy(doc) for doc in self.docs if self._matches(doc, query)),
            None,
        )

    async def insert_one(self, doc: dict[str, Any]) -> None:
        BSON.encode(doc)
        if await self.find_one({"_id": doc["_id"]}):
            raise DuplicateKeyError("duplicate movie id")
        self.docs.append(deepcopy(doc))

    async def update_one(self, query: dict[str, Any], update: dict[str, Any]) -> None:
        BSON.encode(update["$set"])
        for doc in self.docs:
            if self._matches(doc, query):
                doc.update(deepcopy(update["$set"]))
                return

    async def delete_one(self, query: dict[str, Any]):
        for index, doc in enumerate(self.docs):
            if self._matches(doc, query):
                self.docs.pop(index)
                return type("DeleteResult", (), {"deleted_count": 1})()
        return type("DeleteResult", (), {"deleted_count": 0})()

    @classmethod
    def _matches(cls, doc: dict[str, Any], query: dict[str, Any]) -> bool:
        for key, condition in query.items():
            if key == "$or":
                if not any(cls._matches(doc, item) for item in condition):
                    return False
                continue
            value = doc.get(key)
            if isinstance(condition, dict):
                if "$ne" in condition and value == condition["$ne"]:
                    return False
                if "$exists" in condition and (key in doc) != condition["$exists"]:
                    return False
                if "$elemMatch" in condition:
                    matcher = condition["$elemMatch"]
                    regex = re.compile(matcher["$regex"], re.IGNORECASE)
                    if not any(regex.search(str(item)) for item in value or []):
                        return False
            elif isinstance(value, list):
                if condition == []:
                    if value:
                        return False
                elif condition not in value:
                    return False
            elif value != condition:
                return False
        return True


class FakeDatabase:
    def __init__(self) -> None:
        self.movies = FakeCollection()
        self.movie_metadata = FakeCollection()
        self.movie_metadata.docs = [
            {
                "_id": "movie_options",
                "languages": ["English", "Hindi", "Telugu", "Tamil", "Kannada", "Malayalam"],
                "formats": ["2D", "3D", "IMAX 2D", "IMAX 3D", "4DX", "Dolby Atmos"],
                "ratings": ["U", "UA", "A", "S"],
            }
        ]


@pytest.fixture
def fake_db() -> FakeDatabase:
    return FakeDatabase()


@pytest_asyncio.fixture
async def client(fake_db: FakeDatabase):
    db = fake_db
    app.dependency_overrides[get_database] = lambda: db
    with patch("app.main.connect_db"), patch("app.main.close_db"):
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://testserver",
        ) as test_client:
            yield test_client
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_movie_crud_requires_admin_and_persists_updates(client: AsyncClient) -> None:
    payload = {
        "id": "mov_inception",
        "title": "Inception",
        "duration_minutes": 148,
        "languages": ["English"],
        "formats": ["IMAX 2D"],
        "release_date": "2026-11-24",
    }

    forbidden = await client.post("/api/v1/movies", json=payload)
    assert forbidden.status_code == 403

    created = await client.post(
        "/api/v1/movies",
        json=payload,
        headers={"X-User-Role": "ADMIN"},
    )
    assert created.status_code == 201
    assert created.json()["id"] == "mov_inception"
    assert created.json()["release_date"] == "2026-11-24"

    updated = await client.patch(
        "/api/v1/movies/mov_inception",
        json={"title": "Inception: Reissue", "release_date": "2026-12-01"},
        headers={"X-User-Role": "ADMIN"},
    )
    assert updated.status_code == 200
    assert updated.json()["title"] == "Inception: Reissue"
    assert updated.json()["release_date"] == "2026-12-01"

    deleted = await client.delete(
        "/api/v1/movies/mov_inception",
        headers={"X-User-Role": "ADMIN"},
    )
    assert deleted.status_code == 204
    assert (await client.get("/api/v1/movies/mov_inception")).status_code == 404


@pytest.mark.asyncio
async def test_movie_list_filters_city_language_format_and_active_status(
    client: AsyncClient,
) -> None:
    headers = {"X-User-Role": "ADMIN"}
    movies = [
        {
            "id": "mov_global",
            "title": "Global",
            "duration_minutes": 110,
            "languages": ["English"],
            "formats": ["2D"],
        },
        {
            "id": "mov_city",
            "title": "City Match",
            "duration_minutes": 125,
            "languages": ["Hindi"],
            "formats": ["IMAX 2D"],
            "city_ids": ["city_hyd"],
        },
        {
            "id": "mov_inactive",
            "title": "Inactive",
            "duration_minutes": 95,
            "is_active": False,
        },
        {
            "id": "mov_other_city",
            "title": "Other City",
            "duration_minutes": 140,
            "city_ids": ["city_blr"],
        },
    ]
    for movie in movies:
        created = await client.post("/api/v1/movies", json=movie, headers=headers)
        assert created.status_code == 201

    response = await client.get(
        "/api/v1/movies",
        params={"city": "city_hyd", "language": "hInDi", "format": "imax 2d"},
    )
    assert response.status_code == 200
    assert [movie["id"] for movie in response.json()] == ["mov_city"]

    include_inactive = await client.get(
        "/api/v1/movies",
        params={"city_id": "city_hyd", "active_only": "false"},
    )
    assert {movie["id"] for movie in include_inactive.json()} == {
        "mov_global",
        "mov_city",
        "mov_inactive",
    }


@pytest.mark.asyncio
async def test_movie_options_are_read_from_mongodb_and_allow_custom_values(
    client: AsyncClient,
    fake_db: FakeDatabase,
) -> None:
    options = fake_db.movie_metadata.docs[0]
    options["languages"] = ["Japanese"]
    options["formats"] = ["ScreenX"]
    options["ratings"] = ["PG-13"]

    response = await client.get("/api/v1/movies/meta")
    assert response.status_code == 200
    assert response.json() == {
        "languages": ["Japanese"],
        "formats": ["ScreenX"],
        "ratings": ["PG-13"],
    }

    created = await client.post(
        "/api/v1/movies",
        headers={"X-User-Role": "ADMIN"},
        json={
            "id": "mov_custom",
            "title": "Custom Options",
            "duration_minutes": 100,
            "rating": "PG-13",
            "languages": ["Japanese"],
            "formats": ["ScreenX"],
        },
    )
    assert created.status_code == 201

    invalid = await client.post(
        "/api/v1/movies",
        headers={"X-User-Role": "ADMIN"},
        json={
            "id": "mov_invalid",
            "title": "Unsupported Option",
            "duration_minutes": 100,
            "languages": ["English"],
        },
    )
    assert invalid.status_code == 422
    assert (await client.post("/api/v1/movies/meta")).status_code == 405


@pytest.mark.asyncio
async def test_startup_seeds_movie_options_only_when_missing() -> None:
    database = SimpleNamespace(movies=AsyncMock(), movie_metadata=AsyncMock())
    mongo_client = MagicMock()
    mongo_client.__getitem__.return_value = database

    with (
        patch(
            "app.core.db.get_settings",
            return_value=SimpleNamespace(
                mongo_uri="mongodb://localhost",
                mongo_db_name="BookMyShow",
            ),
        ),
        patch("app.core.db.AsyncIOMotorClient", return_value=mongo_client),
    ):
        await connect_db()
        database.movie_metadata.update_one.assert_awaited_once_with(
            {"_id": MOVIE_OPTIONS_ID},
            {"$setOnInsert": DEFAULT_MOVIE_OPTIONS},
            upsert=True,
        )
        await close_db()
