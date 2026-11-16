import asyncio
from unittest.mock import AsyncMock, patch

from asgiref.sync import sync_to_async
from django.test import TestCase

from search.models import DistributorSourceModel
from search.services.browser_service import BrowserManager
from search.services.product import Product
from search.services.search_service import stream_search

from ..fixtures.playwright import (
    MockBrowser,
    MockChromium,
    MockContext,
    MockPage,
    MockPlaywright,
    return_html,
)
from ..fixtures.products import sample_product, sample_product_2


async def mock_fetch_result(context, distributor: DistributorSourceModel, query) -> Product:
    if distributor.name == "SlowShop":
        await asyncio.sleep(0.1)
        return sample_product
    await asyncio.sleep(0.01)
    return sample_product_2


def failing_playwright() -> MockPlaywright:
    playwright = MockPlaywright()
    playwright.chromium = MockChromium(launch_error=RuntimeError("chromium launch failed"))
    return playwright


def create_distributors(count: int) -> None:
    """
    Creates active distributors with distinct base urls so every search
    misses the cache and fetches through the concurrency cap.
    """
    for i in range(count):
        DistributorSourceModel.objects.create(
            name=f"Shop{i}",
            base_url=f"https://shop{i}.com/",
            search_string="search?q=%s",
            currency="EUR",
            included_vat=10,
            product_name_selector="#name",
            product_url_selector="a",
            product_picture_url_selector="img",
            product_price_selector="div > span",
            active=True,
        )


class FastElement:
    async def wait_for(self, timeout=0, **kwargs) -> None:
        return


class FastLocator:
    first = FastElement()


class CountingPage(MockPage):
    def __init__(self, tracker: dict) -> None:
        super().__init__()
        self.tracker = tracker

    async def goto(self, *args) -> bool:
        self.url = args[0]
        await asyncio.sleep(0.02)
        return True

    async def content(self, *args) -> str:
        query = self.url.split("?q=")[1]
        await asyncio.sleep(0.02)
        return return_html[query]

    def locator(self, *args) -> FastLocator:
        return FastLocator()

    async def close(self, *args) -> None:
        self.tracker["active"] -= 1


class CountingContext(MockContext):
    def __init__(self, tracker: dict) -> None:
        super().__init__()
        self.tracker = tracker

    async def new_page(self, *args) -> CountingPage:
        page = CountingPage(self.tracker)
        self.tracker["active"] += 1
        self.tracker["max_active"] = max(self.tracker["max_active"], self.tracker["active"])
        return page


class CountingBrowser(MockBrowser):
    def __init__(self, tracker: dict) -> None:
        super().__init__()
        self.tracker = tracker

    async def new_context(self, *args) -> CountingContext:
        return CountingContext(self.tracker)


class CountingChromium(MockChromium):
    def __init__(self, tracker: dict) -> None:
        super().__init__()
        self.tracker = tracker

    async def launch(self, *args, **kwargs) -> CountingBrowser:
        self.launches += 1
        self.launch_args = kwargs.get("args")
        return CountingBrowser(self.tracker)


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

    @patch("search.services.browser_service.async_playwright", return_value=MockPlaywright())
    @patch("search.services.search_service.fetch_result", side_effect=mock_fetch_result)
    @patch("search.services.search_service.browser_manager", new=BrowserManager(idle_timeout=0))
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

    @patch("search.services.browser_service.async_playwright", return_value=MockPlaywright())
    async def test_stream_search_no_active_distributors(self, mock_playwright):
        await sync_to_async(DistributorSourceModel.objects.all().delete)()
        products = [product async for product in stream_search("test")]
        self.assertEqual(products, [])
        # No distributors means no browser launch at all.
        mock_playwright.assert_not_called()

    @patch("search.services.browser_service.asyncio.sleep", new_callable=AsyncMock)
    @patch("search.services.browser_service.async_playwright", return_value=failing_playwright())
    @patch("search.services.search_service.browser_manager", new=BrowserManager(idle_timeout=0))
    async def test_stream_search_browser_unavailable(self, mock_playwright, mock_sleep):
        # Three failed launch attempts (backoff skipped) abort the stream
        # gracefully instead of crashing it.
        products = [product async for product in stream_search("test")]
        self.assertEqual(products, [])
        self.assertEqual(mock_playwright.return_value.chromium.launches, 3)

    async def test_stream_search_caps_concurrent_fetches(self):
        await sync_to_async(DistributorSourceModel.objects.all().delete)()
        await sync_to_async(create_distributors)(12)

        tracker = {"active": 0, "max_active": 0}
        playwright = MockPlaywright()
        playwright.chromium = CountingChromium(tracker)

        with (
            patch("search.services.search_service.browser_manager", new=BrowserManager(idle_timeout=0)),
            patch("search.services.browser_service.async_playwright", return_value=playwright),
            patch("search.services.fetcher.SEARCH_CONCURRENCY_LIMIT", 2),
            patch("search.services.fetcher._fetch_semaphore", None),
        ):
            products = [product async for product in stream_search("test")]

        # Every distributor still yields a product, but at most two pages
        # (i.e. two concurrent fetches) are open at any moment.
        self.assertEqual(len(products), 12)
        self.assertEqual(tracker["max_active"], 2)