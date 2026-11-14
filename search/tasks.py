import asyncio

from celery import shared_task
from django.core.cache import cache

from search.services.probes import probe_all
from search.services.stats import (
    TOP_SEARCHES_CACHE_KEY,
    TOP_SEARCHES_LIMIT,
    get_top_queries,
)


@shared_task
def update_top_search_queries() -> list[dict[str, str | int]]:
    top = get_top_queries(TOP_SEARCHES_LIMIT)
    cache.set(TOP_SEARCHES_CACHE_KEY, top, timeout=None)
    return top


@shared_task
def probe_distributors(distributor_ids: list[int] | None = None) -> str:
    """
    Probes active distributors (all of them when distributor_ids is None)
    and returns a one-line summary of the run.
    """
    return asyncio.run(probe_all(distributor_ids))
