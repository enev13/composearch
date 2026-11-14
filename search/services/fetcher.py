import asyncio
import logging
from urllib.parse import urljoin

from decouple import config
from django.core.cache import cache
from playwright.async_api import BrowserContext

from search.models import DistributorSourceModel
from search.services.product import Product

CACHE_TIMEOUT: float = config("CACHE_TIMEOUT", cast=float, default=60 * 60)
BROWSER_TIMEOUT: float = config("BROWSER_TIMEOUT", cast=float, default=15_000)
SEARCH_CONCURRENCY_LIMIT: int = config("SEARCH_CONCURRENCY_LIMIT", cast=int, default=6)

log = logging.getLogger(__name__)

# Process-wide cap on concurrent distributor page fetches; created lazily
# in the running event loop on first use.
_fetch_semaphore: asyncio.Semaphore | None = None


def _get_fetch_semaphore() -> asyncio.Semaphore:
    """
    Returns the process-wide semaphore capping concurrent distributor
    page fetches, creating it lazily on first use.

    Reads the module globals on every call so tests can reconfigure the
    limit or force a fresh semaphore.
    """
    global _fetch_semaphore
    if _fetch_semaphore is None:
        _fetch_semaphore = asyncio.Semaphore(SEARCH_CONCURRENCY_LIMIT)
    return _fetch_semaphore


async def fetch_result(
    context: BrowserContext, distributor: DistributorSourceModel, query: str
) -> Product | None:
    """
    Takes a BrowserContext of the shared browser, a DistributorSourceModel and a search query.

    Checks for the given url in the cache.
    If the url is not in the cache, fetches the url and stores the result in the cache.

    Returns a Product object if the product could be parsed.
    If the price selector does not appear, returns None.
    If an exception occurs, returns None.
    """
    url = urljoin(distributor.base_url, distributor.search_string.replace("%s", query))
    price_selector = distributor.product_price_selector

    # Checks if the url is in the cache.
    cached_content = cache.get(url, None)

    # If the url is in the cache, parses the result.
    if cached_content:
        log.debug(f"Using cached url: {url}, length: {len(cached_content)}")
        return await Product.from_html(distributor=distributor, html_content=cached_content)

    # If the url is not in the cache, fetches the url under the
    # process-wide concurrency cap.
    html_content = ""
    async with _get_fetch_semaphore():
        page = await context.new_page()
        try:
            await page.goto(url)
            price_loaded = page.locator(price_selector).first
            await price_loaded.wait_for(timeout=BROWSER_TIMEOUT / 2)
            html_content = await page.content()
            log.debug(f"Fetched url: {url}, length: {len(html_content)}")
        except Exception:
            log.debug(f"Error fetching url: {url}", exc_info=True)
        finally:
            await page.close()

    # If the url is fetched successfully, parses the result into a Product object.
    product = None
    if html_content:
        product = await Product.from_html(distributor=distributor, html_content=html_content)

    # If the product could be parsed, stores the result in the cache,
    # otherwise stores the result in the cache for a much shorter time.
    if product:
        cache.set(key=url, value=html_content, timeout=CACHE_TIMEOUT)
    else:
        cache.set(key=url, value=html_content, timeout=CACHE_TIMEOUT / 10)

    return product
