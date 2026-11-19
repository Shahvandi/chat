
import asyncio
import time

from django.conf import settings
from redis.asyncio import Redis


# ==========================================
# CONFIGURATION
# ==========================================

CONNECTION_TTL_MS = 45_000
SWEEP_INTERVAL = 10

_client = None


# ==========================================
# IN-MEMORY STORAGE (DEBUG MODE)
# ==========================================

_memory_connections = {}
_memory_versions = {}
_memory_version_counter = 0

_memory_lock = asyncio.Lock()


# ==========================================
# REDIS LUA SCRIPTS (PRODUCTION)
# ==========================================

REGISTER_SCRIPT = """
local t = redis.call('TIME')
local now = (t[1] * 1000) + math.floor(t[2] / 1000)
local expiry = now + tonumber(ARGV[3])

redis.call('ZREMRANGEBYSCORE', KEYS[1], '-inf', now)

local was_online = redis.call('ZCARD', KEYS[1]) > 0

redis.call('ZADD', KEYS[1], expiry, ARGV[2])

local latest = redis.call('ZREVRANGE', KEYS[1], 0, 0, 'WITHSCORES')

redis.call('ZADD', KEYS[2], latest[2], ARGV[1])

local version = tonumber(redis.call('HGET', KEYS[4], ARGV[1]) or '0')

if not was_online then
    version = redis.call('INCR', KEYS[3])
    redis.call('HSET', KEYS[4], ARGV[1], version)

    return {1, version}
end

return {0, version}
"""


HEARTBEAT_SCRIPT = """
local t = redis.call('TIME')
local now = (t[1] * 1000) + math.floor(t[2] / 1000)
local expiry = now + tonumber(ARGV[3])

redis.call('ZREMRANGEBYSCORE', KEYS[1], '-inf', now)

if not redis.call('ZSCORE', KEYS[1], ARGV[2]) then
    return 0
end

redis.call('ZADD', KEYS[1], expiry, ARGV[2])

local latest = redis.call('ZREVRANGE', KEYS[1], 0, 0, 'WITHSCORES')

redis.call('ZADD', KEYS[2], latest[2], ARGV[1])

return 1
"""


DISCONNECT_SCRIPT = """
local t = redis.call('TIME')
local now = (t[1] * 1000) + math.floor(t[2] / 1000)

redis.call('ZREMRANGEBYSCORE', KEYS[1], '-inf', now)

redis.call('ZREM', KEYS[1], ARGV[2])

if redis.call('ZCARD', KEYS[1]) == 0 then

    local removed = redis.call('ZREM', KEYS[2], ARGV[1])

    if removed == 1 then
        local version = redis.call('INCR', KEYS[3])

        redis.call('HSET', KEYS[4], ARGV[1], version)

        return {1, version}
    end
end

local latest = redis.call('ZREVRANGE', KEYS[1], 0, 0, 'WITHSCORES')

if latest[2] then
    redis.call('ZADD', KEYS[2], latest[2], ARGV[1])
end

local version = tonumber(redis.call('HGET', KEYS[4], ARGV[1]) or '0')

return {0, version}
"""


SWEEP_SCRIPT = """
local t = redis.call('TIME')
local now = (t[1] * 1000) + math.floor(t[2] / 1000)

local expired = redis.call('ZRANGEBYSCORE', KEYS[1], '-inf', now)

local events = {}

for _, user_id in ipairs(expired) do

    local connections_key = ARGV[1] .. user_id .. ':connections'

    redis.call('ZREMRANGEBYSCORE', connections_key, '-inf', now)

    if redis.call('ZCARD', connections_key) == 0 then

        local removed = redis.call('ZREM', KEYS[1], user_id)

        if removed == 1 then

            local version = redis.call('INCR', KEYS[2])

            redis.call('HSET', KEYS[3], user_id, version)

            table.insert(events, user_id)
            table.insert(events, tostring(version))

        end

    else

        local latest = redis.call(
            'ZREVRANGE',
            connections_key,
            0,
            0,
            'WITHSCORES'
        )

        redis.call('ZADD', KEYS[1], latest[2], user_id)

    end

end

return events
"""


SNAPSHOT_SCRIPT = """
local t = redis.call('TIME')
local now = (t[1] * 1000) + math.floor(t[2] / 1000)

local users = redis.call(
    'ZRANGEBYSCORE',
    KEYS[1],
    now + 1,
    '+inf'
)

local result = {}

for _, user_id in ipairs(users) do

    table.insert(result, user_id)

    table.insert(
        result,
        redis.call('HGET', KEYS[2], user_id) or '0'
    )

end

return result
"""


# ==========================================
# REDIS HELPERS
# ==========================================

def _keys(user_id):
    prefix = settings.PRESENCE_REDIS_PREFIX

    return (
        f"{prefix}:user:{user_id}:connections",
        f"{prefix}:online",
        f"{prefix}:version_counter",
        f"{prefix}:versions",
    )


def get_redis():
    global _client

    if _client is None:

        _client = Redis(
            host=settings.REDIS_HOST,
            port=settings.REDIS_PORT,
            db=settings.REDIS_DB,
            username=settings.REDIS_USERNAME or None,
            password=settings.REDIS_PASSWORD or None,
            decode_responses=True,
            socket_connect_timeout=5,
            socket_timeout=5,
            health_check_interval=30,
        )

    return _client


# ==========================================
# IN-MEMORY HELPERS
# ==========================================

async def _memory_register(user_id, connection_id):
    global _memory_version_counter

    async with _memory_lock:

        now = time.monotonic()

        connections = _memory_connections.setdefault(
            user_id,
            {}
        )

        for cid, expiry in list(connections.items()):

            if expiry <= now:
                connections.pop(cid, None)

        was_online = bool(connections)

        connections[connection_id] = now + (
            CONNECTION_TTL_MS / 1000
        )

        if not was_online:

            _memory_version_counter += 1

            _memory_versions[user_id] = (
                _memory_version_counter
            )

        return (
            not was_online,
            _memory_versions.get(user_id, 0)
        )


async def _memory_refresh(user_id, connection_id):

    async with _memory_lock:

        now = time.monotonic()

        connections = _memory_connections.get(
            user_id,
            {}
        )

        expiry = connections.get(connection_id)

        if expiry is None:
            return False

        if expiry <= now:

            connections.pop(connection_id, None)

            return False

        connections[connection_id] = now + (
            CONNECTION_TTL_MS / 1000
        )

        return True


async def _memory_remove(user_id, connection_id):
    global _memory_version_counter

    async with _memory_lock:

        now = time.monotonic()

        connections = _memory_connections.get(user_id)

        if connections is None:

            return (
                False,
                _memory_versions.get(user_id, 0)
            )

        was_online = any(
            expiry > now
            for expiry in connections.values()
        )

        connections.pop(connection_id, None)

        for cid, expiry in list(connections.items()):

            if expiry <= now:
                connections.pop(cid, None)

        if connections:

            return (
                False,
                _memory_versions.get(user_id, 0)
            )

        _memory_connections.pop(user_id, None)

        if was_online:

            _memory_version_counter += 1

            version = _memory_version_counter

            _memory_versions[user_id] = version

            return True, version

        return (
            False,
            _memory_versions.get(user_id, 0)
        )


async def _memory_snapshot():

    async with _memory_lock:

        now = time.monotonic()

        result = []

        for user_id, connections in _memory_connections.items():

            is_online = any(
                expiry > now
                for expiry in connections.values()
            )

            if is_online:

                result.append({
                    'user_id': user_id,
                    'version': _memory_versions.get(
                        user_id,
                        0
                    ),
                })

        return result


async def _memory_sweep_locked():
    global _memory_version_counter

    now = time.monotonic()

    expired_users = []

    for user_id in list(_memory_connections.keys()):

        connections = _memory_connections[user_id]

        for connection_id, expiry in list(connections.items()):

            if expiry <= now:
                connections.pop(connection_id, None)

        if not connections:

            _memory_connections.pop(user_id, None)

            _memory_version_counter += 1

            version = _memory_version_counter

            _memory_versions[user_id] = version

            expired_users.append(
                (user_id, version)
            )

    return expired_users


async def _memory_sweep():

    async with _memory_lock:

        return await _memory_sweep_locked()


# ==========================================
# PUBLIC PRESENCE API
# ==========================================

async def register_connection(user_id, connection_id):

    user_id = str(user_id)
    connection_id = str(connection_id)

    if settings.DEBUG:

        return await _memory_register(
            user_id,
            connection_id
        )

    redis = get_redis()

    keys = _keys(user_id)

    result = await redis.eval(
        REGISTER_SCRIPT,
        4,
        keys[0],
        keys[1],
        keys[2],
        keys[3],
        user_id,
        connection_id,
        CONNECTION_TTL_MS,
    )

    return (
        bool(int(result[0])),
        int(result[1])
    )


async def refresh_connection(user_id, connection_id):

    user_id = str(user_id)
    connection_id = str(connection_id)

    if settings.DEBUG:

        return await _memory_refresh(
            user_id,
            connection_id
        )

    redis = get_redis()

    keys = _keys(user_id)

    result = await redis.eval(
        HEARTBEAT_SCRIPT,
        2,
        keys[0],
        keys[1],
        user_id,
        connection_id,
        CONNECTION_TTL_MS,
    )

    return bool(result)


async def remove_connection(user_id, connection_id):

    user_id = str(user_id)
    connection_id = str(connection_id)

    if settings.DEBUG:

        return await _memory_remove(
            user_id,
            connection_id
        )

    redis = get_redis()

    keys = _keys(user_id)

    result = await redis.eval(
        DISCONNECT_SCRIPT,
        4,
        keys[0],
        keys[1],
        keys[2],
        keys[3],
        user_id,
        connection_id,
    )

    return (
        bool(int(result[0])),
        int(result[1])
    )


async def get_online_snapshot():

    if settings.DEBUG:

        return await _memory_snapshot()

    redis = get_redis()

    prefix = settings.PRESENCE_REDIS_PREFIX

    result = await redis.eval(
        SNAPSHOT_SCRIPT,
        2,
        f"{prefix}:online",
        f"{prefix}:versions",
    )

    return [
        {
            'user_id': result[index],
            'version': int(result[index + 1]),
        }
        for index in range(0, len(result), 2)
    ]


async def sweep_expired_connections():

    if settings.DEBUG:

        return await _memory_sweep()

    redis = get_redis()

    prefix = settings.PRESENCE_REDIS_PREFIX

    result = await redis.eval(
        SWEEP_SCRIPT,
        3,
        f"{prefix}:online",
        f"{prefix}:version_counter",
        f"{prefix}:versions",
        f"{prefix}:user:",
    )

    return [
        (
            result[index],
            int(result[index + 1])
        )
        for index in range(0, len(result), 2)
    ]


# ==========================================
# CLEANUP
# ==========================================

async def close_redis_connection():

    global _client

    if settings.DEBUG:
        return

    if _client is not None:

        await _client.aclose()

        _client = None
