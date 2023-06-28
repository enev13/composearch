from django.test import TestCase
from .fixtures import sample_product, sample_product_0_vat

from search.models import DistributorSourceModel
from search.product import DEFAULT_PICTURE, Product


class TestParseHTML(TestCase):
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

    async def test_parse_html_normal_html(self):
        product = await Product.from_html(self.distributor, self.html)
        self.assertEqual(product, sample_product)

    async def test_parse_html_0_vat(self):
        product = await Product.from_html(self.distributor_0_vat, self.html)
        self.assertEqual(product, sample_product_0_vat)

    async def test_parse_html_no_name(self):
        product = await Product.from_html(self.distributor, self.html_no_name)
        self.assertIsNone(product)

    async def test_parse_html_no_url(self):
        product = await Product.from_html(self.distributor, self.html_no_url)
        self.assertIsNone(product)

    async def test_parse_html_no_picture(self):
        product = await Product.from_html(self.distributor, self.html_no_picture)
        self.assertIsNotNone(product)
        self.assertEqual(product.picture_url, DEFAULT_PICTURE)

    async def test_parse_html_no_price(self):
        product = await Product.from_html(self.distributor, self.html_no_price)
        self.assertIsNone(product)

    async def test_parse_html_no_product(self):
        product = await Product.from_html(self.distributor, self.html_no_product)
        self.assertIsNone(product)

    async def test_parse_html_no_result(self):
        product = await Product.from_html(self.distributor, "")
        self.assertIsNone(product)
