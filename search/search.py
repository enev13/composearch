import asyncio
import logging
from decimal import Decimal
from urllib.parse import quote_plus, urljoin

from asgiref.sync import sync_to_async
from decouple import config
from django.core.cache import cache
from django.templatetags.static import static
from playwright.async_api import BrowserContext, async_playwright

from search.helpers import to_decimal
from search.models import DistributorSourceModel
from search.parser import Parser
from search.product import Product

DEFAULT_PICTURE = static("images/device.png")
CACHE_TIMEOUT = config("CACHE_TIMEOUT", cast=int, default=60 * 60)
BROWSER_TIMEOUT = config("BROWSER_TIMEOUT", cast=int, default=15_000)

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
        context = await browser.new_context()
        context.set_default_timeout(BROWSER_TIMEOUT)
        tasks = [fetch_result(context, distributor, query) for distributor in distributors]
        results = await asyncio.gather(*tasks)
        await context.close()
        await browser.close()

    results = filter(None, results)
    results = sorted(results, key=lambda product: product.price) if results else []
    return results


@sync_to_async
def get_active_distributors() -> list[DistributorSourceModel]:
    """
    Returns a list of all active DistributorSourceModels.
    """
    return list(DistributorSourceModel.objects.filter(active=True))


async def fetch_result(context: BrowserContext, distributor: DistributorSourceModel, query) -> Product | None:
    """
    Takes a BrowserContext, a DistributorSourceModel and a search query.

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
        product = await parse_html(distributor, cached_content)
        return product

    # If the url is not in the cache, fetches the url.
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

    # If the url is fetched successfully, parses the result.
    if html_content:
        product = await parse_html(distributor, html_content)

    # If the product could be parsed, stores the result in the cache,
    # otherwise stores the result in the cache for a much shorter time.
    if product:
        cache.set(url, html_content, CACHE_TIMEOUT)
    else:
        cache.set(url, html_content, CACHE_TIMEOUT / 10)

    return product


async def parse_html(distributor: DistributorSourceModel, result: str) -> Product | None:
    """
    Takes a DistributorSourceModels and a html string.

    Parses the result and returns a Product object.
    If an error occurs or the product could not be parsed, returns None.
    """
    if not distributor or not result:
        return None

    async with Parser(parser="bs4") as parser:
        await parser.load_content(result)
        product_name = await parser.select_element(distributor.product_name_selector, "text")
        if product_name:
            try:
                currency = distributor.currency
                vat = distributor.included_vat

                price = await parser.select_element(distributor.product_price_selector, "text")
                price = to_decimal(price)
                price /= 1 + Decimal(vat / 100)

                url = await parser.select_element(distributor.product_url_selector, "href")
                url = url.replace(distributor.base_url, "")
                url = url[1:] if url.startswith("/") else url
                url = urljoin(distributor.base_url, url)

                picture_url = await parser.select_element(distributor.product_picture_url_selector, "src")
                if picture_url:
                    picture_url = picture_url.replace(distributor.base_url, "")
                    picture_url = picture_url[1:] if picture_url.startswith("/") else picture_url
                    picture_url = urljoin(distributor.base_url, picture_url)
                else:
                    picture_url = DEFAULT_PICTURE
                product = Product(
                    name=product_name,
                    price=price,
                    currency=currency,
                    vat=vat,
                    url=url,
                    picture_url=picture_url,
                    shop=distributor.name,
                    shop_icon=urljoin(distributor.base_url, "favicon.ico"),
                )
                return product
            except Exception as ex:
                log.debug(f"ERROR: {distributor.name}: {ex}")
        else:
            log.debug(f"Product name not found for {distributor.name}")
