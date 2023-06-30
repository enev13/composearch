import time

from django.test import TestCase

from search.models import DistributorSourceModel
from search.search import fetch_result
from search.tests.fixtures.playwright import CONTENT_TIME, WAIT_FOR_TIME, MockBrowser
from search.tests.fixtures.products import sample_product, sample_product_2


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

    async def test_fetch_result_not_from_cache(self):
        start_time = time.time()
        product = await fetch_result(self.browser, self.distributor, "test2")
        end_time = time.time()
        self.assertEqual(product, sample_product_2)
        self.assertGreaterEqual(end_time - start_time, CONTENT_TIME + WAIT_FOR_TIME)

    async def test_fetch_result_from_cache(self):
        product = await fetch_result(self.browser, self.distributor, "test")
        # Second time should be faster
        start_time = time.time()
        product = await fetch_result(self.browser, self.distributor, "test")
        end_time = time.time()
        self.assertEqual(product, sample_product)
        self.assertLess(end_time - start_time, CONTENT_TIME + WAIT_FOR_TIME)
