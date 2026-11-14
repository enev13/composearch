from __future__ import annotations

import logging
from dataclasses import dataclass
from decimal import Decimal
from urllib.parse import urljoin

from django.templatetags.static import static

from search.models import DistributorSourceModel
from search.parsers import Parser
from search.utils.helpers import to_decimal

DEFAULT_PICTURE: str = static("images/device.png")
log = logging.getLogger(__name__)


@dataclass
class Product:
    """Dataclass for storing product information."""

    name: str
    price: Decimal
    currency: str
    vat: int
    url: str
    shop: str
    shop_icon: str
    picture_url: str

    def to_dict(self) -> dict[str, str]:
        """
        Returns a JSON-safe dict representation of the product.
        """
        return {
            "name": self.name,
            "price": str(self.price),
            "currency": self.currency,
            "vat": self.vat,
            "url": self.url,
            "shop": self.shop,
            "shop_icon": self.shop_icon,
            "picture_url": self.picture_url,
        }

    @staticmethod
    async def from_html(
        distributor: DistributorSourceModel | None, html_content: str, parser: str = "bs4"
    ) -> Product | None:
        """
        Takes a DistributorSourceModel and a html string.

        Parses the result and returns a Product object.
        If an error occurs or the product could not be parsed, returns None.
        """
        if not distributor or not html_content:
            return None

        async with Parser(parser=parser) as p:
            await p.load_content(html_content)
            product_name = await p.select_element(
                selector=distributor.product_name_selector, type="text"
            )
            if product_name:
                try:
                    currency = distributor.currency
                    vat = distributor.included_vat

                    price = await p.select_element(
                        selector=distributor.product_price_selector, type="text"
                    )
                    price = to_decimal(price)
                    price /= 1 + Decimal(vat / 100)
                    price = round(price, 2)

                    url = await p.select_element(selector=distributor.product_url_selector, type="href")
                    url = url.replace(distributor.base_url, "")
                    url = url.removeprefix("/")
                    url = urljoin(distributor.base_url, url)

                    picture_url = await p.select_element(
                        selector=distributor.product_picture_url_selector, type="src"
                    )
                    if picture_url:
                        picture_url = picture_url.replace(distributor.base_url, "")
                        picture_url = picture_url.removeprefix("/")
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
                    log.debug(f"ERROR: {distributor.name}: {ex}", exc_info=True)
                    return None
            else:
                log.debug(f"Product name not found for {distributor.name}")
                return None
