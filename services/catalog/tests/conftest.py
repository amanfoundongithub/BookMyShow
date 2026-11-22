from collections import defaultdict
from typing import Any
from unittest.mock import AsyncMock, patch
import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from app.core.cache import get_redis
from app.core.db import get_database
from app.main import app


class FakeCursor:
    def __init__(self, docs: list[dict[str, Any]]) -> None:
        self._docs = list(docs)

    def sort(self, field: str, direction: int) -> "FakeCursor":
        reverse = direction == -1
        self._docs.sort(key=lambda d: d.get(field), reverse=reverse)
        return self

    async def to_list(self, length: int = 200) -> list[dict[str, Any]]:
        return self._docs[:length]


class FakeCollection:
    def __init__(self, initial_docs: list[dict[str, Any]] | None = None) -> None:
        self.docs: list[dict[str, Any]] = [dict(d) for d in (initial_docs or [])]

    def find(self, query: dict[str, Any] | None = None) -> FakeCursor:
        query = query or {}
        matched = [d for d in self.docs if self._matches(d, query)]
        return FakeCursor(matched)

    async def find_one(self, query: dict[str, Any]) -> dict[str, Any] | None:
        for doc in self.docs:
            if self._matches(doc, query):
                return dict(doc)
        return None

    async def distinct(self, field: str, query: dict[str, Any] | None = None) -> list[Any]:
        query = query or {}
        values: list[Any] = []
        for doc in self.docs:
            if self._matches(doc, query) and field in doc:
                val = doc[field]
                if val not in values:
                    values.append(val)
        return values

    async def insert_one(self, doc: dict[str, Any]) -> None:
        self.docs.append(dict(doc))

    @staticmethod
    def _matches(doc: dict[str, Any], query: dict[str, Any]) -> bool:
        for key, cond in query.items():
            val = doc.get(key)
            if isinstance(cond, dict):
                if "$in" in cond and val not in cond["$in"]:
                    return False
                if "$gte" in cond and (val is None or val < cond["$gte"]):
                    return False
                if "$lte" in cond and (val is None or val > cond["$lte"]):
                    return False
            else:
                if val != cond:
                    return False
        return True


class FakeDatabase:
    def __init__(self) -> None:
        self._collections: dict[str, FakeCollection] = defaultdict(FakeCollection)

    def __getattr__(self, name: str) -> FakeCollection:
        return self._collections[name]

    async def command(self, cmd: str) -> dict[str, Any]:
        if cmd == "ping":
            return {"ok": 1}
        return {"ok": 0}


@pytest.fixture
def fake_db() -> FakeDatabase:
    return FakeDatabase()


@pytest.fixture
def cache_store() -> dict[str, Any]:
    return {}


@pytest_asyncio.fixture
async def client(fake_db: FakeDatabase, cache_store: dict[str, Any]):
    async def _override_db():
        return fake_db

    async def _fake_get_json(key: str):
        return cache_store.get(key)

    async def _fake_set_json(key: str, value: Any, ttl_seconds: int):
        cache_store[key] = value

    async def _fake_delete_pattern(pattern: str):
        prefix = pattern.rstrip("*")
        keys_to_delete = [k for k in cache_store if k.startswith(prefix)]
        for k in keys_to_delete:
            del cache_store[k]

    mock_redis = AsyncMock()
    mock_redis.ping = AsyncMock(return_value=True)

    app.dependency_overrides[get_database] = _override_db
    app.dependency_overrides[get_redis] = lambda: mock_redis

    with (
        patch("app.main.connect_mongo", new=AsyncMock()),
        patch("app.main.close_mongo", new=AsyncMock()),
        patch("app.main.connect_redis", new=AsyncMock()),
        patch("app.main.close_redis", new=AsyncMock()),
        patch("app.services.catalog_service.cache_get_json", side_effect=_fake_get_json),
        patch("app.services.catalog_service.cache_set_json", side_effect=_fake_set_json),
        patch("app.services.catalog_service.cache_delete_pattern", side_effect=_fake_delete_pattern),
    ):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://testserver") as ac:
            yield ac

    app.dependency_overrides.clear()