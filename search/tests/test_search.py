from decimal import Decimal
from unittest.mock import patch

from django.test import TestCase
from playwright.async_api import Browser

from search.models import DistributorSourceModel
from search.search import DEFAULT_PICTURE, get_active_distributors, parse_results, perform_search, to_decimal


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

    def test_parse_results_normal_html(self):
        products = parse_results([self.distributor], [self.html])
        self.assertEqual(products[0].name, "Test product")
        self.assertEqual(products[0].url, "https://test.com/test-product")
        self.assertEqual(products[0].picture_url, "https://test.com/test-product.jpg")
        self.assertEqual(products[0].price, Decimal("9.08"))
        self.assertEqual(products[0].currency, "EUR")
        self.assertEqual(products[0].vat, 10)
        self.assertEqual(products[0].shop, "TestShop")
        self.assertEqual(products[0].shop_icon, "https://test.com/favicon.ico")

    def test_parse_results_0_vat(self):
        products = parse_results([self.distributor_0_vat], [self.html])
        self.assertEqual(products[0].name, "Test product")
        self.assertEqual(products[0].url, "https://test.com/test-product")
        self.assertEqual(products[0].picture_url, "https://test.com/test-product.jpg")
        self.assertEqual(products[0].price, Decimal("9.99"))
        self.assertEqual(products[0].currency, "EUR")
        self.assertEqual(products[0].vat, 0)
        self.assertEqual(products[0].shop, "TestShop")
        self.assertEqual(products[0].shop_icon, "https://test.com/favicon.ico")

    def test_parse_results_no_name(self):
        products = parse_results([self.distributor], [self.html_no_name])
        self.assertEqual(products, [])

    def test_parse_results_no_url(self):
        products = parse_results([self.distributor], [self.html_no_url])
        self.assertEqual(products, [])

    def test_parse_results_no_picture(self):
        products = parse_results([self.distributor], [self.html_no_picture])
        self.assertEqual(products[0].picture_url, DEFAULT_PICTURE)

    def test_parse_results_no_price(self):
        products = parse_results([self.distributor], [self.html_no_price])
        self.assertEqual(products, [])

    def test_parse_results_no_product(self):
        products = parse_results([self.distributor], [self.html_no_product])
        self.assertEqual(products, [])

    def test_parse_results_no_distributor(self):
        products = parse_results([], [self.html])
        self.assertEqual(products, [])

    def test_parse_results_no_result(self):
        products = parse_results([self.distributor], [])
        self.assertEqual(products, [])

    def test_parse_results_no_distributor_no_result(self):
        products = parse_results([], [])
        self.assertEqual(products, [])

    async def mock_fetch_url(browser: Browser, url: str, price_selector: str) -> str:
        return """
        <html>
            <body>
                <div id="name">Test product</div>
                <a href="https://test.com/test-product">Test product</a>
                <img src="https://test.com/test-product.jpg">
                <div><span class="price">9.99</span></div>
            </body>
        </html>
        """

    @patch("search.search.fetch_url", side_effect=mock_fetch_url)
    async def test_perform_search(self, mock_fetch_url):
        products = await perform_search("test")
        self.assertEqual(products[0].name, "Test product")
        self.assertEqual(products[0].url, "https://test.com/test-product")
        self.assertEqual(products[0].picture_url, "https://test.com/test-product.jpg")
        self.assertEqual(products[0].price, Decimal("9.08"))
        self.assertEqual(products[0].currency, "EUR")
        self.assertEqual(products[0].vat, 10)
        self.assertEqual(products[0].shop, "TestShop")
        self.assertEqual(products[0].shop_icon, "https://test.com/favicon.ico")
