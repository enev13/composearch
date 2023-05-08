from dataclasses import dataclass
import requests
from bs4 import BeautifulSoup

from search.models import DistributorSourceModel


@dataclass
class Product:
    name: str
    price: str
    currency: str
    vat: bool
    url: str
    picture_url: str


def perform_search(query):
    results = []

    for distributor in DistributorSourceModel.objects.all():
        product = Product("", "", "", False, "", "")

        URL = distributor.base_url + distributor.search_string.replace("%s", query)

        page = requests.get(URL)
        print(page)
        soup = BeautifulSoup(page.content, "html.parser")

        product_name = soup.select(distributor.product_name_selector)
        print(product_name)
        if product_name:
            product = Product(
                name=product_name[0].text.strip(),
                price=soup.select(distributor.product_price_selector)[0].text.strip(),
                currency=distributor.currency,
                vat=distributor.including_vat,
                url=distributor.base_url + soup.select(distributor.product_url_selector)[0].text.strip(),
                picture_url=soup.select(distributor.product_picture_url_selector),
            )
            print(product)
        else:
            continue
        results.append(product)
    return results
