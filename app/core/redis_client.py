"""
CleanTrack AI — Redis Client (async)
Used for:
  - arq job queue
  - JWT refresh token blacklist
  - WebSocket pub/sub channel
  - Cache layer
"""
import json
from typing import Any, Optional

import redis.asyncio as aioredis

from app.core.config import get_settings

settings = get_settings()

_redis_pool: Optional[aioredis.Redis] = None


async def get_redis() -> aioredis.Redis:
    """FastAPI dependency — returns shared async Redis connection."""
    global _redis_pool
    if _redis_pool is None:
        _redis_pool = aioredis.from_url(
            settings.redis_url,
            encoding="utf-8",
            decode_responses=True,
            socket_connect_timeout=5,
        )
    return _redis_pool


async def close_redis() -> None:
    global _redis_pool
    if _redis_pool:
        await _redis_pool.aclose()
        _redis_pool = None


# ── Refresh token store ───────────────────────────────────────────────────────
REFRESH_PREFIX = "ct:refresh:"
BLACKLIST_PREFIX = "ct:blacklist:"


async def store_refresh_token(user_id: str, token: str, ttl_seconds: int) -> None:
    r = await get_redis()
    await r.setex(f"{REFRESH_PREFIX}{user_id}", ttl_seconds, token)


async def validate_refresh_token(user_id: str, token: str) -> bool:
    r = await get_redis()
    stored = await r.get(f"{REFRESH_PREFIX}{user_id}")
    return stored == token


async def revoke_refresh_token(user_id: str) -> None:
    r = await get_redis()
    await r.delete(f"{REFRESH_PREFIX}{user_id}")


async def blacklist_access_token(jti: str, ttl_seconds: int) -> None:
    r = await get_redis()
    await r.setex(f"{BLACKLIST_PREFIX}{jti}", ttl_seconds, "1")


async def is_token_blacklisted(jti: str) -> bool:
    r = await get_redis()
    return bool(await r.exists(f"{BLACKLIST_PREFIX}{jti}"))


# ── WebSocket pub/sub ─────────────────────────────────────────────────────────
CHANNEL_DASHBOARD = "ct:ws:dashboard"
CHANNEL_REPORT_PREFIX = "ct:ws:report:"


async def publish_event(channel: str, payload: dict) -> None:
    r = await get_redis()
    await r.publish(channel, json.dumps(payload))


async def get_pubsub() -> aioredis.client.PubSub:
    r = await get_redis()
    return r.pubsub()
