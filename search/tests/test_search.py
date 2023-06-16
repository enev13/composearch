from decimal import Decimal
from unittest.mock import patch

from django.test import TestCase
from playwright.async_api import BrowserContext

from search.models import DistributorSourceModel
from search.product import Product
from search.search import DEFAULT_PICTURE, get_active_distributors, parse_html, perform_search, to_decimal


class TestSearch(TestCase):
    def setUp(self) -> None:
        self.distributor = DistributorSourceModel.objects.create(
            name="TestShop",
            base_url="https://test.com/",
            search_string="search?q=%s",
            currency="EUR",
            included_vat=10,
            product_name_selector="#name",
            product_url_selector="a",
            product_picture_url_selector="img",
            product_price_selector="div > span",
            active=True,
        )
        self.distributor_0_vat = DistributorSourceModel.objects.create(
            name="TestShop",
            base_url="https://test.com/",
            search_string="search?q=%s",
            currency="EUR",
            included_vat=0,
            product_name_selector="#name",
            product_url_selector="a",
            product_picture_url_selector="img",
            product_price_selector="div > span",
            active=True,
        )
        self.distributor_inactive = DistributorSourceModel.objects.create(
            name="TestShop",
            base_url="https://test.com/",
            search_string="search?q=%s",
            currency="EUR",
            included_vat=0,
            product_name_selector="#name",
            product_url_selector="a",
            product_picture_url_selector="img",
            product_price_selector="div > span",
            active=False,
        )

        self.html = """
        <html>
            <body>
                <div id="name">Test product</div>
                <a href="https://test.com/test-product">Test product</a>
                <img src="https://test.com/test-product.jpg">
                <div><span class="price">9.99</span></div>
            </body>
        </html>
        """
        self.html_no_name = """
        <html>
            <body>
                <a href="https://test.com/test-product"></a>
                <img src="https://test.com/test-product.jpg">
                <div><span class="price">9.99</span></div>
            </body>
        </html>
        """
        self.html_no_url = """
        <html>
            <body>
                <div id="name">Test product</div>
                <img src="https://test.com/test-product.jpg">
                <div><span class="price">9.99</span></div>
            </body>
        </html>
        """
        self.html_no_picture = """
        <html>
            <body>
                <div id="name">Test product</div>
                <a href="https://test.com/test-product">Test product</a>
                <div><span class="price">9.99</span></div>
            </body>
        </html>
        """
        self.html_no_price = """
        <html>
            <body>
                <div id="name">Test product</div>
                <a href="https://test.com/test-product">Test product</a>
                <img src="https://test.com/test-product.jpg">
            </body>
        </html>
        """
        self.html_no_product = """
        <html>
            <body>
            </body>
        </html>
        """

    async def test_get_distributors(self):
        self.assertEqual(await get_active_distributors(), [self.distributor, self.distributor_0_vat])

    def test_to_float(self):
        self.assertEqual(to_decimal("1.23"), Decimal("1.23"))
        self.assertEqual(to_decimal("1,23"), Decimal("1.23"))
        self.assertEqual(to_decimal(" -1.23"), Decimal("-1.23"))
        self.assertEqual(to_decimal("1 234.56"), Decimal("1234.56"))
        self.assertEqual(to_decimal("1,234.56"), Decimal("1234.56"))
        self.assertEqual(to_decimal("1"), Decimal("1.0"))
        self.assertEqual(to_decimal("1.23abc"), Decimal("1.23"))
        self.assertEqual(to_decimal("Price: 1.23 EUR"), Decimal("1.23"))
        self.assertEqual(to_decimal("1.234.56"), Decimal("1234.56"))
        self.assertEqual(to_decimal("not a float"), None)

    async def test_parse_html_normal_html(self):
        product = await parse_html(self.distributor, self.html)
        self.assertEqual(product.name, "Test product")
        self.assertEqual(product.url, "https://test.com/test-product")
        self.assertEqual(product.picture_url, "https://test.com/test-product.jpg")
        self.assertEqual(product.price, Decimal("9.08"))
        self.assertEqual(product.currency, "EUR")
        self.assertEqual(product.vat, 10)
        self.assertEqual(product.shop, "TestShop")
        self.assertEqual(product.shop_icon, "https://test.com/favicon.ico")

    async def test_parse_html_0_vat(self):
        product = await parse_html(self.distributor_0_vat, self.html)
        self.assertEqual(product.name, "Test product")
        self.assertEqual(product.url, "https://test.com/test-product")
        self.assertEqual(product.picture_url, "https://test.com/test-product.jpg")
        self.assertEqual(product.price, Decimal("9.99"))
        self.assertEqual(product.currency, "EUR")
        self.assertEqual(product.vat, 0)
        self.assertEqual(product.shop, "TestShop")
        self.assertEqual(product.shop_icon, "https://test.com/favicon.ico")

    async def test_parse_html_no_name(self):
        product = await parse_html(self.distributor, self.html_no_name)
        self.assertEqual(product, None)

    async def test_parse_html_no_url(self):
        product = await parse_html(self.distributor, self.html_no_url)
        self.assertEqual(product, None)

    async def test_parse_html_no_picture(self):
        product = await parse_html(self.distributor, self.html_no_picture)
        self.assertEqual(product.picture_url, DEFAULT_PICTURE)

    async def test_parse_html_no_price(self):
        product = await parse_html(self.distributor, self.html_no_price)
        self.assertEqual(product, None)

    async def test_parse_html_no_product(self):
        product = await parse_html(self.distributor, self.html_no_product)
        self.assertEqual(product, None)

    async def test_parse_html_no_distributor(self):
        product = await parse_html(None, self.html)
        self.assertEqual(product, None)

    async def test_parse_html_no_result(self):
        product = await parse_html(self.distributor, "")
        self.assertEqual(product, None)

    async def test_parse_html_no_distributor_no_result(self):
        product = await parse_html(None, "")
        self.assertEqual(product, None)

    async def mock_fetch_result(
        context: BrowserContext, distributor: DistributorSourceModel, query
    ) -> Product | None:
        return Product(
            name="Test product",
            url="https://test.com/test-product",
            picture_url="https://test.com/test-product.jpg",
            price=Decimal("9.08"),
            currency="EUR",
            vat=10,
            shop="TestShop",
            shop_icon="https://test.com/favicon.ico",
        )

    @patch("search.search.fetch_result", side_effect=mock_fetch_result)
    async def test_perform_search(self, mock_fetch_results):
        products = await perform_search("test")
        self.assertEqual(products[0].name, "Test product")
        self.assertEqual(products[0].url, "https://test.com/test-product")
        self.assertEqual(products[0].picture_url, "https://test.com/test-product.jpg")
        self.assertEqual(products[0].price, Decimal("9.08"))
        self.assertEqual(products[0].currency, "EUR")
        self.assertEqual(products[0].vat, 10)
        self.assertEqual(products[0].shop, "TestShop")
        self.assertEqual(products[0].shop_icon, "https://test.com/favicon.ico")
