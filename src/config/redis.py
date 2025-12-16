"""Redis configuration for Celery and caching."""

import redis.asyncio as aioredis
from typing import Optional
from .settings import settings

_redis_client: Optional[aioredis.Redis] = None


async def get_redis() -> aioredis.Redis:
    """Get or create Redis client."""
    global _redis_client
    if _redis_client is None:
        _redis_client = await aioredis.from_url(
            settings.redis_url,
            encoding="utf-8",
            decode_responses=True,
        )
    return _redis_client


async def close_redis() -> None:
    """Close Redis connection."""
    global _redis_client
    if _redis_client:
        await _redis_client.close()
        _redis_client = None


# Synchronous Redis client for Celery
try:
    import redis as sync_redis

    redis_client = sync_redis.from_url(
        settings.redis_url,
        decode_responses=True,
    )
except ImportError:
    redis_client = None  # Will be initialized when needed

