import asyncio
import logging
from collections.abc import AsyncIterator
from urllib.parse import quote_plus

from asgiref.sync import sync_to_async

from search.models import DistributorSourceModel
from search.services.browser_service import browser_manager
from search.services.fetcher import BROWSER_TIMEOUT, fetch_result
from search.services.product import Product

log = logging.getLogger(__name__)


async def perform_search(query: str) -> list[Product]:
    """
    Takes a search query, fetches the urls of all active distributors and performs the search.

    Returns a list of Product objects, sorted by price.
    If an error occurs, returns an empty list.
    """
    distributors = await get_active_distributors()
    query = quote_plus(query.encode("utf-8").strip().lower())

    if not distributors:
        return []

    try:
        context = await browser_manager.new_context(default_timeout_ms=BROWSER_TIMEOUT)
    except Exception:
        log.exception("Browser unavailable; aborting search.")
        return []

    try:
        tasks = [fetch_result(context, distributor, query) for distributor in distributors]
        results = await asyncio.gather(*tasks)
    finally:
        await context.close()
        browser_manager.touch()

    # Remove None values and sort by price
    results = filter(None, results)
    results = sorted(results, key=lambda product: product.price) if results else []
    return results


async def stream_search(query: str) -> AsyncIterator[Product]:
    """
    Streams products as each active distributor returns them.

    Yields each non-None Product in completion order (fastest first), so the
    browser can render results progressively via Server-Sent Events.
    """
    distributors = await get_active_distributors()
    query = quote_plus(query.encode("utf-8").strip().lower())

    if not distributors:
        return

    try:
        context = await browser_manager.new_context(default_timeout_ms=BROWSER_TIMEOUT)
    except Exception:
        log.exception("Browser unavailable; aborting stream.")
        return

    try:
        tasks = [
            fetch_result(context, distributor, query)
            for distributor in distributors
        ]
        for completed in asyncio.as_completed(tasks):
            product = await completed
            if product is not None:
                yield product
    finally:
        await context.close()
        browser_manager.touch()


@sync_to_async
def get_active_distributors() -> list[DistributorSourceModel]:
    """
    Returns a list of all active DistributorSourceModels.
    """
    return list(DistributorSourceModel.objects.filter(active=True))
