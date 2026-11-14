import logging

import redis
from decouple import config
from django.core.cache import cache

logger = logging.getLogger(__name__)

TOP_SEARCHES_LIMIT: int = config("TOP_SEARCHES_LIMIT", default=100, cast=int)
TOP_SEARCHES_CACHE_KEY: str = "top_search_queries"
REDIS_SORTED_SET_KEY: str = "composearch:search_queries"


def _get_redis() -> redis.Redis | None:
    try:
        return redis.Redis.from_url(
            config("REDIS_URL", default="redis://localhost:6379/0")
        )
    except Exception:
        logger.warning("Failed to create Redis client", exc_info=True)
        return None


def record_query(query: str) -> None:
    normalized = query.strip().lower()
    if not normalized:
        return
    try:
        r = _get_redis()
        if r:
            r.zincrby(REDIS_SORTED_SET_KEY, 1, normalized)
    except Exception:
        logger.warning("Failed to record search query in Redis", exc_info=True)


def get_top_queries(limit: int = TOP_SEARCHES_LIMIT) -> list[dict[str, str | int]]:
    try:
        r = _get_redis()
        if not r:
            return []
        items = r.zrevrange(REDIS_SORTED_SET_KEY, 0, limit - 1, withscores=True)
        return [
            {
                "query": (q.decode() if isinstance(q, bytes) else q),
                "count": int(score),
            }
            for q, score in items
        ]
    except Exception:
        logger.warning("Failed to fetch top search queries from Redis", exc_info=True)
        return []


def get_top_search_queries_cached(limit: int = TOP_SEARCHES_LIMIT) -> list[dict[str, str | int]]:
    cached = cache.get(TOP_SEARCHES_CACHE_KEY)
    if cached is not None:
        return cached
    top = get_top_queries(limit)
    cache.set(TOP_SEARCHES_CACHE_KEY, top, timeout=None if top else 300)
    return top
