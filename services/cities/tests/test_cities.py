from copy import deepcopy
from typing import Any
from unittest.mock import patch
import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from pymongo.errors import DuplicateKeyError
from app.core.db import get_database
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

    def find(self) -> FakeCursor:
        return FakeCursor([deepcopy(doc) for doc in self.docs])

    async def find_one(self, query: dict[str, Any]) -> dict[str, Any] | None:
        return next(
            (deepcopy(doc) for doc in self.docs if all(doc.get(k) == v for k, v in query.items())),
            None,
        )

    async def insert_one(self, doc: dict[str, Any]) -> None:
        if await self.find_one({"_id": doc["_id"]}):
            raise DuplicateKeyError("duplicate city id")
        self.docs.append(deepcopy(doc))

    async def update_one(self, query: dict[str, Any], update: dict[str, Any]) -> None:
        for doc in self.docs:
            if all(doc.get(k) == v for k, v in query.items()):
                doc.update(deepcopy(update["$set"]))
                return

    async def delete_one(self, query: dict[str, Any]):
        for index, doc in enumerate(self.docs):
            if all(doc.get(k) == v for k, v in query.items()):
                self.docs.pop(index)
                return type("DeleteResult", (), {"deleted_count": 1})()
        return type("DeleteResult", (), {"deleted_count": 0})()


class FakeDatabase:
    def __init__(self) -> None:
        self.cities = FakeCollection()


@pytest_asyncio.fixture
async def client():
    db = FakeDatabase()
    db.cities.docs = [
        {"_id": "city_blr", "name": "Bengaluru", "state": "Karnataka", "country": "India"},
        {"_id": "city_hyd", "name": "Hyderabad", "state": "Telangana", "country": "India"},
    ]
    app.dependency_overrides[get_database] = lambda: db
    with patch("app.main.connect_db"), patch("app.main.close_db"):
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://testserver",
        ) as test_client:
            yield test_client
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_list_and_get_cities(client: AsyncClient) -> None:
    listed = await client.get("/api/v1/cities")
    assert listed.status_code == 200
    assert [city["id"] for city in listed.json()] == ["city_blr", "city_hyd"]

    found = await client.get("/api/v1/cities/city_hyd")
    assert found.status_code == 200
    assert found.json()["name"] == "Hyderabad"
    assert (await client.get("/api/v1/cities/city_missing")).status_code == 404


@pytest.mark.asyncio
async def test_city_crud_requires_admin(client: AsyncClient) -> None:
    payload = {
        "id": "city_pune",
        "name": "Pune",
        "state": "Maharashtra",
        "country": "India",
    }

    forbidden = await client.post("/api/v1/cities", json=payload)
    assert forbidden.status_code == 403

    created = await client.post(
        "/api/v1/cities",
        json=payload,
        headers={"X-User-Role": "ADMIN"},
    )
    assert created.status_code == 201
    assert created.json()["id"] == "city_pune"

    updated = await client.patch(
        "/api/v1/cities/city_pune",
        json={"name": "Pune City"},
        headers={"X-User-Role": "ADMIN"},
    )
    assert updated.status_code == 200
    assert updated.json()["name"] == "Pune City"

    deleted = await client.delete(
        "/api/v1/cities/city_pune",
        headers={"X-User-Role": "ADMIN"},
    )
    assert deleted.status_code == 204
    assert (await client.get("/api/v1/cities/city_pune")).status_code == 404
