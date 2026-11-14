import asyncio
import time
from unittest.mock import AsyncMock, patch

from django.test import TestCase

from search.services.browser_service import BrowserManager

from ..fixtures.playwright import MockChromium, MockPlaywright


def failing_playwright() -> MockPlaywright:
    playwright = MockPlaywright()
    playwright.chromium = MockChromium(launch_error=RuntimeError("chromium launch failed"))
    return playwright


class TestBrowserManager(TestCase):
    def test_status_before_launch_is_idle(self) -> None:
        manager = BrowserManager(idle_timeout=0)
        self.assertEqual(manager.status(), "idle")

    @patch("search.services.browser_service.async_playwright", return_value=MockPlaywright())
    async def test_acquire_launches_lazily_and_reuses(self, mock_playwright) -> None:
        manager = BrowserManager(idle_timeout=0)
        first = await manager.acquire()
        second = await manager.acquire()
        self.assertEqual(mock_playwright.call_count, 1)
        self.assertIs(first, second)
        self.assertEqual(manager.status(), "running")
        await manager.shutdown()

    @patch("search.services.browser_service.async_playwright", return_value=MockPlaywright())
    async def test_new_context_returns_context_with_default_timeout(self, mock_playwright) -> None:
        manager = BrowserManager(idle_timeout=0)
        context = await manager.new_context(default_timeout_ms=123)
        self.assertEqual(context.default_timeout, 123)
        plain = await manager.new_context()
        self.assertIsNone(plain.default_timeout)
        self.assertEqual(manager.status(), "running")
        await manager.shutdown()

    @patch("search.services.browser_service.async_playwright", return_value=MockPlaywright())
    async def test_acquire_relaunches_dead_browser(self, mock_playwright) -> None:
        manager = BrowserManager(idle_timeout=0)
        browser = await manager.acquire()
        # Simulate a crash between searches.
        browser.connected = False
        self.assertEqual(manager.status(), "dead")
        relaunched = await manager.acquire()
        self.assertIsNot(relaunched, browser)
        self.assertEqual(mock_playwright.return_value.chromium.launches, 2)
        self.assertEqual(manager.status(), "running")
        await manager.shutdown()

    @patch("search.services.browser_service.asyncio.sleep", new_callable=AsyncMock)
    @patch("search.services.browser_service.async_playwright", return_value=failing_playwright())
    async def test_acquire_raises_after_three_failed_launches(self, mock_playwright, mock_sleep) -> None:
        manager = BrowserManager(idle_timeout=0)
        with self.assertRaises(RuntimeError):
            await manager.acquire()
        self.assertEqual(mock_playwright.return_value.chromium.launches, 3)
        # The next acquire starts the backoff sequence over.
        with self.assertRaises(RuntimeError):
            await manager.acquire()
        self.assertEqual(mock_playwright.return_value.chromium.launches, 6)
        # Two exponential-backoff sleeps (2s, 4s) per failed acquire.
        self.assertEqual(mock_sleep.await_count, 4)

    @patch("search.services.browser_service.async_playwright", return_value=MockPlaywright())
    async def test_idle_shutdown_and_relaunch(self, mock_playwright) -> None:
        manager = BrowserManager(idle_timeout=0.4)
        browser = await manager.acquire()
        await asyncio.sleep(1.0)
        self.assertFalse(browser.connected)
        self.assertEqual(manager.status(), "idle")
        relaunched = await manager.acquire()
        self.assertIsNot(relaunched, browser)
        self.assertEqual(mock_playwright.return_value.chromium.launches, 2)
        await manager.shutdown()

    @patch("search.services.browser_service.async_playwright", return_value=MockPlaywright())
    async def test_zero_idle_timeout_never_shuts_down(self, mock_playwright) -> None:
        manager = BrowserManager(idle_timeout=0)
        browser = await manager.acquire()
        await asyncio.sleep(0.3)
        self.assertTrue(browser.connected)
        self.assertIsNone(manager._watcher)
        self.assertEqual(manager.status(), "running")
        await manager.shutdown()

    @patch("search.services.browser_service.async_playwright", return_value=MockPlaywright())
    async def test_touch_resets_idle_deadline(self, mock_playwright) -> None:
        manager = BrowserManager(idle_timeout=0.4)
        await manager.acquire()
        # Pretend the browser has been idle almost to the timeout, then
        # record activity before the watcher can act on the stale mark.
        manager._last_used = time.monotonic() - 0.39
        manager.touch()
        await asyncio.sleep(0.25)
        self.assertEqual(manager.status(), "running")
        await manager.shutdown()

    @patch("search.services.browser_service.async_playwright", return_value=MockPlaywright())
    async def test_shutdown_is_idempotent(self, mock_playwright) -> None:
        manager = BrowserManager(idle_timeout=0.4)
        await manager.acquire()
        self.assertEqual(manager.status(), "running")
        await manager.shutdown()
        await manager.shutdown()
        await manager.shutdown()
        self.assertEqual(manager.status(), "idle")
        self.assertIsNone(manager._watcher)
        self.assertEqual(mock_playwright.return_value.chromium.launches, 1)