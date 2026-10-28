from celery import shared_task
from django.core.cache import cache

from search.stats import (
    TOP_SEARCHES_CACHE_KEY,
    TOP_SEARCHES_LIMIT,
    get_top_queries,
)


@shared_task
def update_top_search_queries():
    top = get_top_queries(TOP_SEARCHES_LIMIT)
    cache.set(TOP_SEARCHES_CACHE_KEY, top, timeout=None)
    return top
