import json
import logging
from typing import Any

import redis.asyncio as aioredis

from app.core.config import get_settings

logger = logging.getLogger(__name__)

_USER_TTL = 300  # seconds

_client: aioredis.Redis | None = None


def _get_client() -> aioredis.Redis:
    global _client
    if _client is None:
        _client = aioredis.from_url(get_settings().redis_url, decode_responses=True)
    return _client


async def cache_get(key: str) -> dict[str, Any] | None:
    try:
        value = await _get_client().get(key)
        return json.loads(value) if value else None
    except Exception as exc:
        logger.warning(
            "Cache get failed — falling back to DB", extra={"key": key, "error": str(exc)}
        )
        return None


async def cache_set(key: str, value: dict[str, Any], ttl: int = _USER_TTL) -> None:
    try:
        await _get_client().setex(key, ttl, json.dumps(value, default=str))
    except Exception as exc:
        logger.warning("Cache set failed", extra={"key": key, "error": str(exc)})


async def cache_delete(key: str) -> None:
    try:
        await _get_client().delete(key)
    except Exception as exc:
        logger.warning("Cache delete failed", extra={"key": key, "error": str(exc)})


def user_cache_key(user_id: int) -> str:
    return f"user:{user_id}"
