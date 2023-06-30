from decimal import Decimal
from search.product import Product


sample_product = Product(
    name="Test product",
    url="https://test.com/test-product",
    picture_url="https://test.com/test-product.jpg",
    price=Decimal("9.08"),
    currency="EUR",
    vat=10,
    shop="TestShop",
    shop_icon="https://test.com/favicon.ico",
)

sample_product_2 = Product(
    name="Test product 2",
    url="https://test.com/test-product-2",
    picture_url="https://test.com/test-product-2.jpg",
    price=Decimal("18.17"),
    currency="EUR",
    vat=10,
    shop="TestShop",
    shop_icon="https://test.com/favicon.ico",
)

sample_product_0_vat = Product(
    name="Test product",
    url="https://test.com/test-product",
    picture_url="https://test.com/test-product.jpg",
    price=Decimal("9.99"),
    currency="EUR",
    vat=0,
    shop="TestShop",
    shop_icon="https://test.com/favicon.ico",
)
