from unittest.mock import patch

from django.test import TestCase
from playwright.async_api import BrowserContext

from search.models import DistributorSourceModel
from search.product import Product
from search.search import perform_search

from .fixtures import sample_product


async def mock_fetch_result(
    browser: BrowserContext, distributor: DistributorSourceModel, query
) -> Product:
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

    @patch("search.search.fetch_result", side_effect=mock_fetch_result)
    async def test_perform_search(self, mock_fetch_result):
        products = await perform_search("test")
        self.assertEqual(products, [sample_product])
