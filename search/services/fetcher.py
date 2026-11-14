import asyncio
import logging
import time
from urllib.parse import urljoin

from decouple import config
from django.core.cache import cache
from playwright.async_api import BrowserContext
from playwright.async_api import TimeoutError as PlaywrightTimeoutError

from search.models import DistributorSourceModel
from search.services.monitoring import record_outcome
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


async def _fetch_and_parse(
    context: BrowserContext,
    distributor: DistributorSourceModel,
    url: str,
    semaphore: asyncio.Semaphore | None = None,
) -> tuple[Product | None, str, float, str]:
    """
    Takes a BrowserContext, a DistributorSourceModel, a search result url and
    an optional semaphore capping concurrent fetches (the process-wide one
    when omitted).

    Fetches the url and parses the HTML into a Product.

    Returns a (product, html_content, response_ms, reason) tuple, where
    reason is "" on success and otherwise a slug naming the failing stage:
    "timeout" (navigation timed out), "navigation_error" (navigation
    failed), "selector_timeout" (price selector never appeared) or
    "parse_error" (page fetched but no product parsed). A failure to open a
    page raises and is not recorded: a broken browser is not a distributor
    health problem.
    """
    if semaphore is None:
        semaphore = _get_fetch_semaphore()
    price_selector = distributor.product_price_selector
    html_content = ""
    # A completed fetch that produces nothing usable is a parse error unless
    # a stage below assigns a more specific reason.
    reason = "parse_error"
    start = end = time.perf_counter()
    async with semaphore:
        page = await context.new_page()
        try:
            start = time.perf_counter()
            try:
                await page.goto(url)
            except PlaywrightTimeoutError:
                reason = "timeout"
                raise
            except Exception:
                reason = "navigation_error"
                raise
            try:
                await page.locator(price_selector).first.wait_for(timeout=BROWSER_TIMEOUT / 2)
            except Exception:
                reason = "selector_timeout"
                raise
            try:
                html_content = await page.content()
            except Exception:
                reason = "navigation_error"
                raise
            end = time.perf_counter()
            log.debug(f"Fetched url: {url}, length: {len(html_content)}")
        except Exception:
            end = time.perf_counter()
            log.debug(f"Error fetching url: {url}", exc_info=True)
        finally:
            await page.close()

    # Parses outside the semaphore so the concurrency cap only covers
    # browser work.
    product = None
    if html_content:
        product = await Product.from_html(distributor=distributor, html_content=html_content)
        if product is None:
            reason = "parse_error"
    if product is not None:
        reason = ""

    response_ms = (end - start) * 1000
    return product, html_content, response_ms, reason


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

    # Checks if the url is in the cache.
    cached_content = cache.get(url, None)

    # If the url is in the cache, parses the result. Cached results are not
    # recorded, as they say nothing about current distributor health.
    if cached_content:
        log.debug(f"Using cached url: {url}, length: {len(cached_content)}")
        return await Product.from_html(distributor=distributor, html_content=cached_content)

    # If the url is not in the cache, fetches the url.
    product, html_content, response_ms, reason = await _fetch_and_parse(context, distributor, url)

    # Records the outcome for distributor health tracking. Recording never
    # breaks a search.
    await record_outcome(distributor, product, response_ms, reason)

    # If the product could be parsed, stores the result in the cache,
    # otherwise stores the result in the cache for a much shorter time.
    if product:
        cache.set(key=url, value=html_content, timeout=CACHE_TIMEOUT)
    else:
        cache.set(key=url, value=html_content, timeout=CACHE_TIMEOUT / 10)

    return product
