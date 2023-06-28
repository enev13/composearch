import asyncio
import logging
from urllib.parse import quote_plus, urljoin

from asgiref.sync import sync_to_async
from decouple import config
from django.core.cache import cache
from playwright.async_api import Browser, async_playwright

from search.models import DistributorSourceModel
from search.product import Product

CACHE_TIMEOUT = config("CACHE_TIMEOUT", cast=float, default=60 * 60)
BROWSER_TIMEOUT = config("BROWSER_TIMEOUT", cast=float, default=15_000)

log = logging.getLogger(__name__)


async def perform_search(query: str) -> list[Product | None]:
    """
    Takes a search query, fetches the urls of all active distributors and performs the search.

    Returns a list of Product objects, sorted by price.
    If an error occurs, returns an empty list.
    """
    distributors = await get_active_distributors()
    query = quote_plus(query.encode("utf-8").strip().lower())

    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch()
        tasks = [fetch_result(browser, distributor, query) for distributor in distributors]
        results = await asyncio.gather(*tasks)
        await browser.close()

    # Remove None values and sort by price
    results = filter(None, results)
    results = sorted(results, key=lambda product: product.price) if results else []
    return results


@sync_to_async
def get_active_distributors() -> list[DistributorSourceModel | None]:
    """
    Returns a list of all active DistributorSourceModels.
    """
    return list(DistributorSourceModel.objects.filter(active=True))


async def fetch_result(browser: Browser, distributor: DistributorSourceModel, query) -> Product | None:
    """
    Takes a Browser, a DistributorSourceModel and a search query.

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

    # If the url is not in the cache, fetches the url.
    context = await browser.new_context()
    context.set_default_timeout(BROWSER_TIMEOUT)
    page = await context.new_page()
    html_content = ""
    product = None
    try:
        await page.goto(url)
        price_loaded = page.locator(price_selector).first
        await price_loaded.wait_for(timeout=BROWSER_TIMEOUT / 2)
        html_content = await page.content()
        log.debug(f"Fetched url: {url}, length: {len(html_content)}")
    except Exception as ex:
        log.debug(f"Error fetching url: {url}")
        log.debug(ex)

    await context.close()

    # If the url is fetched successfully, parses the result into a Product object.
    if html_content:
        product = await Product.from_html(distributor=distributor, html_content=html_content)

    # If the product could be parsed, stores the result in the cache,
    # otherwise stores the result in the cache for a much shorter time.
    if product:
        cache.set(key=url, value=html_content, timeout=CACHE_TIMEOUT)
    else:
        cache.set(key=url, value=html_content, timeout=CACHE_TIMEOUT / 10)

    return product
