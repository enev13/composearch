import asyncio
import logging
import re
from dataclasses import dataclass
from urllib.parse import quote_plus, urljoin

from asgiref.sync import sync_to_async
from bs4 import BeautifulSoup
from playwright.async_api import async_playwright, Browser

from search.models import DistributorSourceModel

DEFAULT_PICTURE = "/static/images/device.png"
log = logging.getLogger(__name__)


@dataclass
class Product:
    """Dataclass for storing product information."""

    name: str
    price: str
    currency: str
    vat: bool
    url: str
    shop: str
    shop_icon: str
    picture_url: str


def to_float(text: str) -> float:
    """
    Takes a string and returns the first float found in the string.
    If no float is found, returns None.
    """
    pattern = r"[-+]?\d{1,3}(?:([.,\s])\d{3})*([.,]\d+)?"
    match = re.search(pattern, text)
    if match:
        if match.group(1):
            return float(match.group().replace(match.group(1), "", 1).replace(",", "."))
        return float(match.group().replace(",", "."))
    else:
        return None


async def fetch_url(browser: Browser, url: str, price_selector: str) -> str | None:
    """
    Fetches the given url and waits for the price selector to appear.
    If the price selector does not appear, returns None.
    If an exception occurs, returns None.
    Returns the page's html content as a string.
    """
    page = await browser.new_page()
    try:
        await page.goto(url)
        price_loaded = page.locator(price_selector)
        await price_loaded.wait_for(timeout=5000)
        html_content = await page.content()
        log.info(f"Fetched url: {url}, length: {len(html_content)}")
        return html_content
    except Exception as ex:
        log.error(f"Error fetching url: {url}")
        log.error(ex)


@sync_to_async
def get_distributors() -> list[DistributorSourceModel]:
    return list(DistributorSourceModel.objects.all())


def parse_results(distributors: list[DistributorSourceModel], results: list[str]) -> list[Product | None]:
    """
    Takes a list of DistributorSourceModels and a list of html strings.
    Parses the results from fetch_url and returns a list of Product objects, sorted by price.
    If an error occurs or the product could not be parsed, returns None.
    """
    products = []
    for result, distributor in zip(results, distributors):
        if result:
            soup = BeautifulSoup(result, "html.parser")
            product_name = soup.select(distributor.product_name_selector)
            if product_name:
                try:
                    name = product_name[0].text.strip()
                    price = to_float(soup.select(distributor.product_price_selector)[0].text.strip())
                    currency = distributor.currency
                    vat = distributor.included_vat
                    price /= 1 + vat / 100
                    url = (
                        soup.select(distributor.product_url_selector)[0]
                        .get("href")
                        .replace(distributor.base_url, "")
                    )
                    url = url[1:] if url.startswith("/") else url
                    url = urljoin(distributor.base_url, url)
                    picture_url = soup.select(distributor.product_picture_url_selector)
                    if picture_url:
                        picture_url = (
                            soup.select(distributor.product_picture_url_selector)[0]
                            .get("src")
                            .replace(distributor.base_url, "")
                        )
                        picture_url = picture_url[1:] if picture_url.startswith("/") else picture_url
                        picture_url = urljoin(distributor.base_url, picture_url)
                    else:
                        picture_url = DEFAULT_PICTURE
                    product = Product(
                        name=name,
                        price=price,
                        currency=currency,
                        vat=vat,
                        url=url,
                        picture_url=picture_url,
                        shop=distributor.name,
                        shop_icon=urljoin(distributor.base_url, "favicon.ico"),
                    )
                except IndexError as ex:
                    log.error(f"{distributor.name}: {ex}")
                    continue
            else:
                log.error(f"Product name not found for {distributor.name}")
                continue
            products.append(product)
            products.sort(key=lambda x: x.price)
    return products


async def perform_search(query: str) -> list[Product | None]:
    """
    Takes a search query, fetches the urls of all active distributors and performs the search.
    Returns a list of Product objects.
    If an error occurs, returns an empty list.
    """
    distributors = await get_distributors()
    distributors = [distributor for distributor in distributors if distributor.active]
    urls = [
        urljoin(distributor.base_url, distributor.search_string.replace("%s", quote_plus(query)))
        for distributor in distributors
    ]
    price_selectors = [distributor.product_price_selector for distributor in distributors]
    async with async_playwright() as playwright:
        browser = await playwright.firefox.launch()
        tasks = [
            fetch_url(browser, url, product_price_selector)
            for url, product_price_selector in zip(urls, price_selectors)
        ]

        results = await asyncio.gather(*tasks)
        await browser.close()

    return parse_results(distributors, results)
