from unittest.mock import patch

from django.test import TestCase
from playwright.async_api import BrowserContext

from search.models import DistributorSourceModel
from search.services.browser_service import BrowserManager
from search.services.product import Product
from search.services.search_service import perform_search

from ..fixtures.playwright import MockPlaywright
from ..fixtures.products import sample_product


async def mock_fetch_result(context: BrowserContext, distributor: DistributorSourceModel, query) -> Product:
    return sample_product


class TestPerformSearch(TestCase):
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

    @patch("search.services.browser_service.async_playwright", return_value=MockPlaywright())
    @patch("search.services.search_service.fetch_result", side_effect=mock_fetch_result)
    @patch("search.services.search_service.browser_manager", new=BrowserManager(idle_timeout=0))
    async def test_perform_search(self, mock_fetch, mock_playwright):
        products = await perform_search("test")
        self.assertEqual(products, [sample_product])
        self.assertEqual(mock_playwright.call_count, 1)