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
log = logging.getLogger(__name__)


async def perform_search(query: str) -> list[Product | None]:
    """
    Takes a search query, fetches the urls of all active distributors and performs the search.
    Returns a list of Product objects, sorted by price.
    If an error occurs, returns an empty list.
    """
    distributors = await get_active_distributors()
    urls = [
        urljoin(distributor.base_url, distributor.search_string.replace("%s", quote_plus(query)))
        for distributor in distributors
    ]
    price_selectors = [distributor.product_price_selector for distributor in distributors]

    results = await fetch_results(urls, price_selectors)

    parsed_results = await parse_results(distributors, results)

    return sorted(parsed_results, key=lambda product: product.price) if parsed_results else []


@sync_to_async
def get_active_distributors() -> list[DistributorSourceModel]:
    """
    Returns a list of all active DistributorSourceModels.
    """
    return list(DistributorSourceModel.objects.filter(active=True))


async def fetch_results(urls, price_selectors):
    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch()
        context = await browser.new_context()
        tasks = [
            fetch_url(context, url, product_price_selector)
            for url, product_price_selector in zip(urls, price_selectors)
        ]
        results = await asyncio.gather(*tasks)
        await context.close()
        await browser.close()
    return results


async def fetch_url(context: BrowserContext, url: str, price_selector: str) -> str | None:
    """
    Fetches the given url and waits for the price selector to appear.
    If the price selector does not appear, returns None.
    If an exception occurs, returns None.
    Returns the page's html content as a string.
    """
    cached_result = cache.get(url)
    if cached_result:
        return cached_result

    page = await context.new_page()
    try:
        await page.goto(url)
        price_loaded = page.locator(price_selector)
        await price_loaded.wait_for(timeout=5000)
        html_content = await page.content()
        log.debug(f"Fetched url: {url}, length: {len(html_content)}")
        cache.set(url, html_content, CACHE_TIMEOUT)
        return html_content
    except Exception as ex:
        log.debug(f"Error fetching url: {url}")
        log.debug(ex)


async def parse_results(
    distributors: list[DistributorSourceModel], results: list[str]
) -> list[Product | None]:
    """
    Takes a list of DistributorSourceModels and a list of html strings.
    Parses the results from fetch_url and returns a list of Product objects.
    If an error occurs or the product could not be parsed, returns None.
    """
    products = []
    for result, distributor in zip(results, distributors):
        if result:
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

                        picture_url = await parser.select_element(
                            distributor.product_picture_url_selector, "src"
                        )
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
                        products.append(product)
                    except Exception as ex:
                        log.debug(f"ERROR: {distributor.name}: {ex}")
                        continue
                else:
                    log.debug(f"Product name not found for {distributor.name}")
                    continue

    return products
