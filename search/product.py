from dataclasses import dataclass
from decimal import Decimal


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
