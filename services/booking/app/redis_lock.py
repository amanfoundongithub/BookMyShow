from typing import Any
from redis.asyncio import Redis

# KEYS[1..N] = lock:show:{show_id}:seat:{seat_id}
# ARGV[1] = booking_id (lock owner value)
# ARGV[2] = ttl_seconds
# ARGV[3] = occupied_set_key ("occupied:show:{show_id}")
# ARGV[4..N+3] = seat_ids
ACQUIRE_LOCKS_LUA = """
local seat_count = tonumber(ARGV[4])
local occupied_key = ARGV[3]
local lock_val = ARGV[1]
local ttl = tonumber(ARGV[2])

-- First verify no requested seat is permanently occupied or already locked
for i = 1, seat_count do
    local seat_id = ARGV[4 + i]
    if redis.call("SISMEMBER", occupied_key, seat_id) == 1 then
        return {0, seat_id, "OCCUPIED"}
    end
    local existing = redis.call("GET", KEYS[i])
    if existing then
        return {0, seat_id, "HELD"}
    end
end

-- All clear: set all keys atomically with TTL
for i = 1, seat_count do
    redis.call("SET", KEYS[i], lock_val, "EX", ttl)
end

return {1, "", "LOCKED"}
"""

# KEYS[1..N] = lock:show:{show_id}:seat:{seat_id}
# ARGV[1] = expected booking_id
RELEASE_LOCKS_LUA = """
local expected_owner = ARGV[1]
local released = 0
for i = 1, #KEYS do
    local current = redis.call("GET", KEYS[i])
    if current == expected_owner then
        redis.call("DEL", KEYS[i])
        released = released + 1
    end
end
return released
"""

# KEYS[1..N] = lock:show:{show_id}:seat:{seat_id}
# ARGV[1] = expected booking_id
# ARGV[2] = occupied_set_key ("occupied:show:{show_id}")
# ARGV[3..N+2] = seat_ids
CONFIRM_LOCKS_LUA = """
local expected_owner = ARGV[1]
local occupied_key = ARGV[2]
local seat_count = #KEYS

for i = 1, seat_count do
    local current = redis.call("GET", KEYS[i])
    if current ~= nil and current ~= expected_owner then
        return {0, "OWNER_MISMATCH"}
    end
end

for i = 1, seat_count do
    redis.call("DEL", KEYS[i])
    redis.call("SADD", occupied_key, ARGV[2 + i])
end

return {1, "CONFIRMED"}
"""


class SeatLockManager:
    def __init__(self, redis: Redis, ttl_seconds: int = 600) -> None:
        self.redis = redis
        self.ttl_seconds = ttl_seconds

    @staticmethod
    def lock_key(show_id: str, seat_id: str) -> str:
        return f"lock:show:{show_id}:seat:{seat_id}"

    @staticmethod
    def occupied_key(show_id: str) -> str:
        return f"occupied:show:{show_id}"

    async def acquire_seats(
        self, show_id: str, seat_ids: list[str], booking_id: str
    ) -> tuple[bool, str | None, str | None]:
        keys = [self.lock_key(show_id, s) for s in seat_ids]
        args: list[Any] = [
            booking_id,
            self.ttl_seconds,
            self.occupied_key(show_id),
            len(seat_ids),
            *seat_ids,
        ]
        result = await self.redis.eval(ACQUIRE_LOCKS_LUA, len(keys), *keys, *args)
        acquired = int(result[0]) == 1
        conflict_seat = result[1] or None
        reason = result[2] or None
        return acquired, conflict_seat, reason

    async def release_seats(
        self, show_id: str, seat_ids: list[str], booking_id: str
    ) -> int:
        if not seat_ids:
            return 0
        keys = [self.lock_key(show_id, s) for s in seat_ids]
        released = await self.redis.eval(RELEASE_LOCKS_LUA, len(keys), *keys, booking_id)
        return int(released)

    async def confirm_seats(
        self, show_id: str, seat_ids: list[str], booking_id: str
    ) -> tuple[bool, str]:
        if not seat_ids:
            return True, "CONFIRMED"
        keys = [self.lock_key(show_id, s) for s in seat_ids]
        result = await self.redis.eval(
            CONFIRM_LOCKS_LUA,
            len(keys),
            *keys,
            booking_id,
            self.occupied_key(show_id),
            *seat_ids,
        )
        return int(result[0]) == 1, str(result[1])

    async def get_show_seat_states(
        self, show_id: str, candidate_seat_ids: list[str]
    ) -> dict[str, str]:
        occupied = set(await self.redis.smembers(self.occupied_key(show_id)))
        states: dict[str, str] = {}
        remaining_keys: list[str] = []
        remaining_seats: list[str] = []

        for seat_id in candidate_seat_ids:
            if seat_id in occupied:
                states[seat_id] = "CONFIRMED"
            else:
                remaining_seats.append(seat_id)
                remaining_keys.append(self.lock_key(show_id, seat_id))

        if remaining_keys:
            lock_vals = await self.redis.mget(*remaining_keys)
            for seat_id, val in zip(remaining_seats, lock_vals):
                states[seat_id] = "HELD" if val else "AVAILABLE"

        return states