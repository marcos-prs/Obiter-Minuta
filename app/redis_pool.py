import redis
from app.config import get_settings

_pool: redis.ConnectionPool | None = None


def get_pool() -> redis.ConnectionPool:
    global _pool
    if _pool is None:
        settings = get_settings()
        _pool = redis.ConnectionPool.from_url(
            settings.redis_url,
            decode_responses=True,
            socket_timeout=5,
        )
    return _pool


def disconnect_pool() -> None:
    global _pool
    if _pool is not None:
        _pool.disconnect()
        _pool = None
