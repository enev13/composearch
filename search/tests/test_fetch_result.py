from typing import Any

from django.test import TestCase
from playwright.async_api import Browser

from search.models import DistributorSourceModel
from search.search import fetch_result

from .fixtures import sample_product

return_html = dict(
    {
        "test": """
                <html>
                    <body>
                        <div id="name">Test product</div>
                        <a href="https://test.com/test-product">Test product</a>
                        <img src="https://test.com/test-product.jpg">
                        <div><span class="price">9.99</span></div>
                    </body>
                </html>
            """,
    },
    default="",
)


class MockElement:
    async def wait_for(self, timeout=0) -> None:
        return


class MockLocator:
    first = MockElement()


class MockPage:
    def __init__(self) -> None:
        self.url = ""

    async def goto(self, *args) -> Any:
        self.url = args[0]
        return True

    async def content(self, *args) -> str:
        query = self.url.split("?q=")[1]
        return return_html[query]

    def locator(self, *args) -> MockLocator:
        return MockLocator()


class MockContext:
    async def new_page(self, *args) -> MockPage:
        return MockPage()

    def set_default_timeout(self, *args) -> None:
        return

    async def close(self, *args) -> None:
        return


class MockBrowser(Browser):
    def __init__(self) -> None:
        pass

    async def new_context(self, *args) -> MockContext:
        return MockContext()

    async def close(self, *args) -> None:
        return


class MockChromium:
    async def launch(self, *args) -> MockBrowser:
        return MockBrowser()


class MockPlaywright:
    async def __aenter__(self) -> MockBrowser:
        return MockBrowser()

    async def __aexit__(self, *args) -> None:
        return

    chromium = MockChromium()


class TestFetchResult(TestCase):
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
        self.browser = MockBrowser()

    async def test_fetch_result(self):
        product = await fetch_result(self.browser, self.distributor, "test")
        self.assertEqual(product, sample_product)

    async def test_fetch_result_no_query(self):
        product = await fetch_result(self.browser, self.distributor, "")
        self.assertIsNone(product)
