import time
from typing import Any

from django.core.cache import cache
from django.test import TestCase
from playwright.async_api import TimeoutError as PlaywrightTimeoutError

from search.models import DistributorSourceModel, DistributorStats
from search.services.fetcher import fetch_result

from ..fixtures.playwright import (
    CONTENT_TIME,
    WAIT_FOR_TIME,
    MockContext,
    MockElement,
    MockLocator,
    MockPage,
)
from ..fixtures.products import sample_product, sample_product_2


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
        self.context = MockContext()

    async def test_fetch_result(self):
        product = await fetch_result(self.context, self.distributor, "test")
        self.assertEqual(product, sample_product)

    async def test_fetch_result_no_query(self):
        product = await fetch_result(self.context, self.distributor, "")
        self.assertIsNone(product)

    async def test_fetch_result_not_from_cache(self):
        start_time = time.time()
        product = await fetch_result(self.context, self.distributor, "test2")
        end_time = time.time()
        self.assertEqual(product, sample_product_2)
        self.assertGreaterEqual(end_time - start_time, CONTENT_TIME + WAIT_FOR_TIME)

    async def test_fetch_result_from_cache(self):
        product = await fetch_result(self.context, self.distributor, "test")
        # Second time should be faster
        start_time = time.time()
        product = await fetch_result(self.context, self.distributor, "test")
        end_time = time.time()
        self.assertEqual(product, sample_product)
        self.assertLess(end_time - start_time, CONTENT_TIME + WAIT_FOR_TIME)


class GotoTimeoutPage(MockPage):
    async def goto(self, *args: Any) -> None:
        raise PlaywrightTimeoutError("Navigation timed out")


class GotoTimeoutContext(MockContext):
    async def new_page(self, *args: Any) -> MockPage:
        return GotoTimeoutPage()


class GotoCrashPage(MockPage):
    async def goto(self, *args: Any) -> None:
        raise RuntimeError("Navigation crashed")


class GotoCrashContext(MockContext):
    async def new_page(self, *args: Any) -> MockPage:
        return GotoCrashPage()


class SelectorTimeoutElement(MockElement):
    async def wait_for(self, timeout: float = 0) -> None:
        raise PlaywrightTimeoutError("Selector timed out")


class SelectorTimeoutLocator(MockLocator):
    def __init__(self) -> None:
        self.first = SelectorTimeoutElement()


class SelectorTimeoutPage(MockPage):
    def locator(self, *args: Any) -> MockLocator:
        return SelectorTimeoutLocator()


class SelectorTimeoutContext(MockContext):
    async def new_page(self, *args: Any) -> MockPage:
        return SelectorTimeoutPage()


NO_PRODUCT_HTML = "<html><body><div>nothing to see here</div></body></html>"


class NoProductPage(MockPage):
    async def content(self, *args: Any) -> str:
        return NO_PRODUCT_HTML


class NoProductContext(MockContext):
    async def new_page(self, *args: Any) -> MockPage:
        return NoProductPage()


class TestFetchResultRecording(TestCase):
    def setUp(self) -> None:
        # The locmem cache is shared across tests in the process, so start
        # from a clean slate to control which urls are cached.
        cache.clear()
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

    async def _stats(self) -> DistributorStats | None:
        return await DistributorStats.objects.filter(distributor=self.distributor).afirst()

    async def test_records_success(self):
        product = await fetch_result(MockContext(), self.distributor, "test")

        self.assertEqual(product, sample_product)
        stats = await self._stats()
        self.assertIsNotNone(stats)
        self.assertEqual(stats.total_attempts, 1)
        self.assertEqual(stats.total_successes, 1)
        self.assertEqual(stats.consecutive_failures, 0)
        self.assertGreater(stats.avg_response_ms, 0)
        self.assertIsNotNone(stats.last_attempt_at)
        self.assertIsNotNone(stats.last_success_at)
        self.assertEqual(stats.last_failure_reason, "")

    async def test_cached_result_not_recorded(self):
        product = await fetch_result(MockContext(), self.distributor, "test")
        self.assertEqual(product, sample_product)

        await DistributorStats.objects.filter(distributor=self.distributor).adelete()

        product = await fetch_result(MockContext(), self.distributor, "test")
        self.assertEqual(product, sample_product)
        self.assertIsNone(await self._stats())

    async def test_records_timeout(self):
        product = await fetch_result(GotoTimeoutContext(), self.distributor, "test")

        self.assertIsNone(product)
        stats = await self._stats()
        self.assertIsNotNone(stats)
        self.assertEqual(stats.total_attempts, 1)
        self.assertEqual(stats.total_successes, 0)
        self.assertEqual(stats.consecutive_failures, 1)
        self.assertEqual(stats.last_failure_reason, "timeout")

    async def test_records_navigation_error(self):
        product = await fetch_result(GotoCrashContext(), self.distributor, "test")

        self.assertIsNone(product)
        stats = await self._stats()
        self.assertIsNotNone(stats)
        self.assertEqual(stats.total_attempts, 1)
        self.assertEqual(stats.total_successes, 0)
        self.assertEqual(stats.consecutive_failures, 1)
        self.assertEqual(stats.last_failure_reason, "navigation_error")

    async def test_records_selector_timeout(self):
        product = await fetch_result(SelectorTimeoutContext(), self.distributor, "test")

        self.assertIsNone(product)
        stats = await self._stats()
        self.assertIsNotNone(stats)
        self.assertEqual(stats.total_attempts, 1)
        self.assertEqual(stats.total_successes, 0)
        self.assertEqual(stats.consecutive_failures, 1)
        self.assertEqual(stats.last_failure_reason, "selector_timeout")

    async def test_records_parse_error(self):
        product = await fetch_result(NoProductContext(), self.distributor, "test")

        self.assertIsNone(product)
        stats = await self._stats()
        self.assertIsNotNone(stats)
        self.assertEqual(stats.total_attempts, 1)
        self.assertEqual(stats.total_successes, 0)
        self.assertEqual(stats.consecutive_failures, 1)
        self.assertEqual(stats.last_failure_reason, "parse_error")
