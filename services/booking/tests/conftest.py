import re
from collections import defaultdict
from typing import Any
from unittest.mock import AsyncMock, patch
import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from app.core.db import get_database
from app.core.redis import get_redis
from app.main import app
from app.ws_manager import ShowWsManager


class FakeBookingsCollection:
    def __init__(self, initial_docs: list[dict[str, Any]] | None = None) -> None:
        self.docs: dict[str, dict[str, Any]] = {
            d["_id"]: dict(d) for d in (initial_docs or [])
        }

    async def insert_one(self, doc: dict[str, Any]) -> None:
        self.docs[doc["_id"]] = dict(doc)

    async def find_one(self, query: dict[str, Any]) -> dict[str, Any] | None:
        if "_id" in query:
            doc = self.docs.get(query["_id"])
            return dict(doc) if doc else None
        for doc in self.docs.values():
            if all(doc.get(k) == v for k, v in query.items()):
                return dict(doc)
        return None

    async def update_one(self, query: dict[str, Any], update: dict[str, Any]) -> None:
        doc = await self.find_one(query)
        if doc and "$set" in update:
            self.docs[doc["_id"]].update(update["$set"])


class FakeBookingDatabase:
    def __init__(self) -> None:
        self.bookings = FakeBookingsCollection()

    async def command(self, cmd: str) -> dict[str, Any]:
        return {"ok": 1} if cmd == "ping" else {"ok": 0}


class FakeRedis:
    def __init__(self) -> None:
        self.kv: dict[str, str] = {}
        self.sets: dict[str, set[str]] = defaultdict(set)
        self.published: list[tuple[str, str]] = []

    async def ping(self) -> bool:
        return True

    async def smembers(self, key: str) -> set[str]:
        return set(self.sets.get(key, set()))

    async def mget(self, *keys: str) -> list[str | None]:
        return [self.kv.get(k) for k in keys]

    async def publish(self, channel: str, message: str) -> int:
        self.published.append((channel, message))
        return 1

    async def eval(self, script: str, numkeys: int, *keys_and_args: Any) -> Any:
        keys = list(keys_and_args[:numkeys])
        args = list(keys_and_args[numkeys:])

        # Branch 1: ACQUIRE_LOCKS_LUA
        if "SISMEMBER" in script:
            booking_id = str(args[0])
            occupied_key = str(args[2])
            seat_count = int(args[3])
            seat_ids = [str(x) for x in args[4 : 4 + seat_count]]

            for i, seat_id in enumerate(seat_ids):
                if seat_id in self.sets[occupied_key]:
                    return [0, seat_id, "OCCUPIED"]
                if keys[i] in self.kv:
                    return [0, seat_id, "HELD"]

            for i in range(seat_count):
                self.kv[keys[i]] = booking_id
            return [1, "", "LOCKED"]

        # Branch 2: RELEASE_LOCKS_LUA
        if "local released = 0" in script:
            expected_owner = str(args[0])
            released = 0
            for k in keys:
                if self.kv.get(k) == expected_owner:
                    del self.kv[k]
                    released += 1
            return released

        # Branch 3: CONFIRM_LOCKS_LUA
        if "SADD" in script:
            expected_owner = str(args[0])
            occupied_key = str(args[1])
            seat_ids = [str(x) for x in args[2 : 2 + len(keys)]]

            for k in keys:
                current = self.kv.get(k)
                if current is not None and current != expected_owner:
                    return [0, "OWNER_MISMATCH"]

            for k, seat_id in zip(keys, seat_ids):
                self.kv.pop(k, None)
                self.sets[occupied_key].add(seat_id)
            return [1, "CONFIRMED"]

        raise AssertionError("Unrecognized Lua script in FakeRedis.eval")


@pytest.fixture
def fake_db() -> FakeBookingDatabase:
    return FakeBookingDatabase()


@pytest.fixture
def fake_redis() -> FakeRedis:
    return FakeRedis()


@pytest.fixture
def published_mq_events() -> list[tuple[str, dict[str, Any]]]:
    return []


@pytest_asyncio.fixture
async def client(
    fake_db: FakeBookingDatabase,
    fake_redis: FakeRedis,
    published_mq_events: list[tuple[str, dict[str, Any]]],
):
    async def _override_db():
        return fake_db

    async def _fake_publish_mq(routing_key: str, payload: dict[str, Any]) -> None:
        published_mq_events.append((routing_key, payload))

    ws_manager = ShowWsManager(redis=fake_redis)  # type: ignore[arg-type]
    mock_http = AsyncMock()

    app.dependency_overrides[get_database] = _override_db
    app.dependency_overrides[get_redis] = lambda: fake_redis

    with (
        patch("app.main.connect_mongo", new=AsyncMock()),
        patch("app.main.close_mongo", new=AsyncMock()),
        patch("app.main.connect_redis", new=AsyncMock()),
        patch("app.main.close_redis", new=AsyncMock()),
        patch("app.main.connect_mq", new=AsyncMock()),
        patch("app.main.close_mq", new=AsyncMock()),
        patch("app.services.booking_service.publish_booking_event", side_effect=_fake_publish_mq),
    ):
        app.state.ws_manager = ws_manager
        app.state.http_client = mock_http
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://testserver") as ac:
            yield ac, mock_http

    app.dependency_overrides.clear()