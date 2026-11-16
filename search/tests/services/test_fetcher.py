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
    async def wait_for(self, timeout: float = 0, **kwargs: Any) -> None:
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


SENECA_SEARCH_HTML = """
<html><body>
    <div id="collapse2"><a href="/en/linee/z111">Z111</a></div>
</body></html>
"""

SENECA_DETAIL_HTML = """
<html><body>
    <div class="sp-buy-description"><strong>Z111</strong></div>
    <div class="item sp-media-image active"><img src="/media/1579/z111.jpg"></div>
    <div>&euro; <span class="price-value-container">168.00</span></div>
</body></html>
"""

SENECA_DETAIL_NO_PRICE_HTML = """
<html><body>
    <div class="sp-buy-description"><strong>Z111</strong></div>
</body></html>
"""


class _LinkLocator:
    def __init__(self, href: str | None = None) -> None:
        self._href = href
        self.first = self

    async def wait_for(self, timeout: float = 0, **kwargs: Any) -> None:
        return None

    async def get_attribute(self, name: str) -> str | None:
        return self._href


class DetailNavigatingPage(MockPage):
    """Page double that serves search HTML, then detail HTML after a link
    follow, mirroring Seneca exposing the price only on the detail page."""

    def __init__(self, detail_html: str, link_href: str = "/en/linee/z111") -> None:
        super().__init__()
        self._detail_html = detail_html
        self._link_href = link_href
        self.navigated_urls: list[str] = []

    async def goto(self, *args: Any) -> Any:
        url = args[0]
        self.navigated_urls.append(url)
        if "prodsearch" in url:
            self._html = SENECA_SEARCH_HTML
        else:
            self._html = self._detail_html
        self.url = url
        return True

    async def content(self, *args: Any) -> str:
        return getattr(self, "_html", "")

    def locator(self, *args: Any) -> MockLocator:
        selector = args[0]
        if "a[href" in selector:
            return _LinkLocator(self._link_href)
        return MockLocator()


class DetailNavigatingContext(MockContext):
    def __init__(self, detail_html: str, link_href: str = "/en/linee/z111") -> None:
        super().__init__()
        self._detail_html = detail_html
        self._link_href = link_href

    async def new_page(self, *args: Any) -> MockPage:
        return DetailNavigatingPage(self._detail_html, self._link_href)


class TestFetchResultDetailPage(TestCase):
    def setUp(self) -> None:
        cache.clear()
        self.distributor = DistributorSourceModel.objects.create(
            name="Seneca",
            base_url="https://www.seneca.it/",
            search_string="en/prodsearch/?q=%s",
            currency="EUR",
            included_vat=0,
            product_name_selector=".sp-buy-description strong",
            product_url_selector='#collapse2 a[href^="/en/"]',
            product_picture_url_selector=".sp-media-image.active img",
            product_price_selector=".price-value-container",
            price_on_detail_page=True,
            active=True,
        )

    async def test_follows_link_to_detail_page(self):
        product = await fetch_result(
            DetailNavigatingContext(SENECA_DETAIL_HTML),
            self.distributor,
            "z111",
        )

        self.assertEqual(product.name, "Z111")
        self.assertEqual(product.price, 168.00)
        self.assertEqual(product.url, "https://www.seneca.it/en/linee/z111")
        self.assertEqual(
            product.picture_url, "https://www.seneca.it/media/1579/z111.jpg"
        )

    async def test_no_price_on_detail_page_is_parse_error(self):
        product = await fetch_result(
            DetailNavigatingContext(SENECA_DETAIL_NO_PRICE_HTML),
            self.distributor,
            "z111",
        )

        self.assertIsNone(product)
        stats = await DistributorStats.objects.filter(distributor=self.distributor).afirst()
        self.assertIsNotNone(stats)
        self.assertEqual(stats.last_failure_reason, "parse_error")
