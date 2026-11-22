import asyncio
import json
import logging
from collections import defaultdict
from fastapi import WebSocket
from redis.asyncio import Redis

logger = logging.getLogger(__name__)


class ShowWsManager:
    def __init__(self, redis: Redis) -> None:
        self.redis = redis
        self._rooms: dict[str, set[WebSocket]] = defaultdict(set)
        self._lock = asyncio.Lock()
        self._listener_task: asyncio.Task | None = None

    @staticmethod
    def channel_name(show_id: str) -> str:
        return f"ws:show:{show_id}"

    async def start(self) -> None:
        if self._listener_task is None:
            self._listener_task = asyncio.create_task(self._pubsub_listener())

    async def stop(self) -> None:
        if self._listener_task is not None:
            self._listener_task.cancel()
            try:
                await self._listener_task
            except asyncio.CancelledError:
                pass
            self._listener_task = None

    async def connect(self, show_id: str, websocket: WebSocket) -> None:
        await websocket.accept()
        async with self._lock:
            self._rooms[show_id].add(websocket)

    async def disconnect(self, show_id: str, websocket: WebSocket) -> None:
        async with self._lock:
            room = self._rooms.get(show_id)
            if room is not None:
                room.discard(websocket)
                if not room:
                    self._rooms.pop(show_id, None)

    async def publish_seat_update(
        self,
        show_id: str,
        seats: list[str],
        status: str,
        booking_id: str | None = None,
    ) -> None:
        payload = {
            "type": "SEAT_STATUS_UPDATE",
            "show_id": show_id,
            "seats": seats,
            "status": status,
            "booking_id": booking_id,
        }
        await self.redis.publish(self.channel_name(show_id), json.dumps(payload))

    async def broadcast_local(self, show_id: str, message: dict) -> None:
        async with self._lock:
            targets = list(self._rooms.get(show_id, ()))

        stale: list[WebSocket] = []
        for ws in targets:
            try:
                await ws.send_json(message)
            except Exception:
                stale.append(ws)

        if stale:
            async with self._lock:
                room = self._rooms.get(show_id)
                if room is not None:
                    for ws in stale:
                        room.discard(ws)

    async def _pubsub_listener(self) -> None:
        pubsub = self.redis.pubsub()
        await pubsub.psubscribe("ws:show:*")
        try:
            async for message in pubsub.listen():
                if message.get("type") != "pmessage":
                    continue
                channel: str = message.get("channel", "")
                show_id = channel.removeprefix("ws:show:")
                try:
                    data = json.loads(message["data"])
                except Exception:
                    logger.warning("Invalid pub/sub payload on %s", channel)
                    continue
                await self.broadcast_local(show_id, data)
        finally:
            await pubsub.punsubscribe("ws:show:*")
            await pubsub.aclose()