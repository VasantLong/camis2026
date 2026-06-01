import logging

import redis.asyncio as aioredis

from app.config import settings

logger = logging.getLogger("camis.redis")

_redis: aioredis.Redis | None = None


async def get_redis() -> aioredis.Redis | None:
    global _redis
    if _redis is None:
        try:
            _redis = aioredis.from_url(settings.redis_url)
            await _redis.ping()
            logger.info("redis connected")
        except Exception:
            logger.warning("redis connection failed, caching/lockout disabled", exc_info=True)
            if _redis is not None:
                try:
                    await _redis.close()
                except Exception:
                    pass
            _redis = None
    elif _redis is not None:
        try:
            await _redis.ping()
        except Exception:
            logger.warning("redis ping failed, reconnecting")
            try:
                await _redis.close()
            except Exception:
                pass
            _redis = None
    return _redis


async def close_redis() -> None:
    global _redis
    if _redis is not None:
        await _redis.close()
        _redis = None
