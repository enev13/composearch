import asyncio
import re
from dataclasses import dataclass
from urllib.parse import urljoin

import aiohttp
from asgiref.sync import sync_to_async
from bs4 import BeautifulSoup

from search.models import DistributorSourceModel

DEFAULT_PICTURE = "/static/images/device.png"


@dataclass
class Product:
    name: str
    price: str
    currency: str
    vat: bool
    url: str
    shop: str
    picture_url: str


def to_float(text):
    pattern = r"\b[-+]?\d{1,3}(?:([.,])\d{3})*([.,]\d+)?\b"
    match = re.search(pattern, text)
    if match:
        if match.group(1) == ",":
            return float(match.group().replace(".", "").replace(",", "."))
        return float(match.group().replace(",", "."))
    else:
        return None


async def fetch_url(session, url):
    async with session.get(url) as response:
        return await response.text()


@sync_to_async
def get_distributors():
    return list(DistributorSourceModel.objects.all())


async def perform_search(query):
    distributors = await get_distributors()
    distributors = [distributor for distributor in distributors if distributor.active]
    urls = [
        distributor.base_url + distributor.search_string.replace("%s", query) for distributor in distributors
    ]
    async with aiohttp.ClientSession() as session:
        session.headers.update(
            {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/113.0.0.0 Safari/537.36"
            }
        )
        session.headers.update({"Accept": "*/*"})
        session.headers.update({"Accept-Encoding": "gzip, deflate, br"})
        session.headers.update({"Connection": "keep-alive"})
        tasks = [fetch_url(session, url) for url in urls]
        results = await asyncio.gather(*tasks)

    products = []
    for result, distributor in zip(results, distributors):
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
                )
            except IndexError as ex:
                print(ex)
                continue
        else:
            continue
        products.append(product)
    return products
