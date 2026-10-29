import asyncio
from unittest.mock import patch

from asgiref.sync import sync_to_async
from django.test import TestCase

from search.models import DistributorSourceModel
from search.product import Product
from search.search import stream_search

from .fixtures.products import sample_product, sample_product_2


async def mock_fetch_result(browser, distributor: DistributorSourceModel, query) -> Product:
    if distributor.name == "SlowShop":
        await asyncio.sleep(0.1)
        return sample_product
    await asyncio.sleep(0.01)
    return sample_product_2


class MockBrowser:
    async def close(self):
        return


class MockChromium:
    def __init__(self):
        self.launch_args = None

    async def launch(self, *args, **kwargs):
        self.launch_args = kwargs.get("args")
        return MockBrowser()


class MockPlaywright:
    def __init__(self):
        self.chromium = MockChromium()

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False


class TestStreamSearch(TestCase):
    def setUp(self) -> None:
        DistributorSourceModel.objects.create(
            name="SlowShop",
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
        DistributorSourceModel.objects.create(
            name="FastShop",
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

    @patch("search.search.async_playwright", return_value=MockPlaywright())
    @patch("search.search.fetch_result", side_effect=mock_fetch_result)
    async def test_stream_search_yields_in_completion_order(self, mock_fetch, mock_playwright):
        # SlowShop is submitted first but FastShop completes first, so the
        # generator must yield fastest-first (completion order).
        products = [product async for product in stream_search("test")]
        self.assertEqual(products, [sample_product_2, sample_product])
        self.assertEqual(mock_playwright.call_count, 1)
        self.assertEqual(
            mock_playwright.return_value.chromium.launch_args,
            ["--disable-dev-shm-usage"],
        )

    @patch("search.search.async_playwright", return_value=MockPlaywright())
    async def test_stream_search_no_active_distributors(self, mock_playwright):
        await sync_to_async(DistributorSourceModel.objects.all().delete)()
        products = [product async for product in stream_search("test")]
        self.assertEqual(products, [])
        mock_playwright.assert_not_called()
