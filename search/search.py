import asyncio
import logging
import re
from dataclasses import dataclass
from urllib.parse import quote_plus, urljoin

from asgiref.sync import sync_to_async
from bs4 import BeautifulSoup
from playwright.async_api import async_playwright

from search.models import DistributorSourceModel

DEFAULT_PICTURE = "/static/images/device.png"
log = logging.getLogger(__name__)


@dataclass
class Product:
    name: str
    price: str
    currency: str
    vat: bool
    url: str
    shop: str
    shop_icon: str
    picture_url: str


def to_float(text) -> float:
    pattern = r"\b[-+]?\d{1,3}(?:([.,])\d{3})*([.,]\d+)?\b"
    match = re.search(pattern, text)
    if match:
        if match.group(1) == ",":
            return float(match.group().replace(".", "").replace(",", "."))
        return float(match.group().replace(",", "."))
    else:
        return None


async def fetch_url(url, price_selector) -> str | None:
    try:
        async with async_playwright() as playwright:
            browser = await playwright.firefox.launch()
            page = await browser.new_page()
            await page.goto(url)
            price_loaded = page.locator(price_selector)
            await price_loaded.wait_for()
            html_content = await page.content()
            await browser.close()
            log.info(f"Fetched url: {url}, length: {len(html_content)}")
            return html_content
    except Exception as ex:
        log.error(f"Error fetching url: {url}")
        log.error(ex)


@sync_to_async
def get_distributors() -> list[DistributorSourceModel]:
    return list(DistributorSourceModel.objects.all())


def parse_results(distributors, results) -> list[Product | None]:
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
                    vat = (distributor.including_vat,)
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
                    log.error(distributor.name, ex)
                    continue
            else:
                log.error(f"Product name not found for {distributor.name}")
                continue
            products.append(product)
            products.sort(key=lambda x: x.price)
    return products


async def perform_search(query) -> list[Product | None]:
    distributors = await get_distributors()
    distributors = [distributor for distributor in distributors if distributor.active]
    urls = [
        urljoin(distributor.base_url, distributor.search_string.replace("%s", quote_plus(query)))
        for distributor in distributors
    ]
    price_selectors = [distributor.product_price_selector for distributor in distributors]
    tasks = [
        fetch_url(url, product_price_selector) for url, product_price_selector in zip(urls, price_selectors)
    ]
    results = await asyncio.gather(*tasks)

    return parse_results(distributors, results)
