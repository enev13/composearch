import asyncio
from typing import Any, Self

from playwright.async_api import Browser

WAIT_FOR_TIME = 1
CONTENT_TIME = 3

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
        "test2": """
                <html>
                    <body>
                        <div id="name">Test product 2</div>
                        <a href="https://test.com/test-product-2">Test product 2</a>
                        <img src="https://test.com/test-product-2.jpg">
                        <div><span class="price">19.99</span></div>
                    </body>
                </html>
            """,
    },
    default="",
)


class MockElement:
    async def wait_for(self, timeout=0) -> None:
        await asyncio.sleep(WAIT_FOR_TIME)


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
        await asyncio.sleep(CONTENT_TIME)
        return return_html[query]

    def locator(self, *args) -> MockLocator:
        return MockLocator()

    async def close(self, *args) -> None:
        return


class MockContext:
    def __init__(self) -> None:
        self.default_timeout = None

    async def new_page(self, *args) -> MockPage:
        return MockPage()

    def set_default_timeout(self, timeout) -> None:
        self.default_timeout = timeout

    async def close(self, *args) -> None:
        return


class MockBrowser(Browser):
    def __init__(self, connected: bool = True) -> None:
        self.connected = connected

    def is_connected(self) -> bool:
        return self.connected

    async def new_context(self, *args) -> MockContext:
        return MockContext()

    async def close(self, *args) -> None:
        self.connected = False


class MockChromium:
    def __init__(self, launch_error: Exception | None = None) -> None:
        self.launch_args = None
        self.launches = 0
        self.launch_error = launch_error

    async def launch(self, *args, **kwargs) -> MockBrowser:
        self.launches += 1
        self.launch_args = kwargs.get("args")
        if self.launch_error is not None:
            raise self.launch_error
        return MockBrowser()


class MockPlaywright:
    def __init__(self) -> None:
        self.chromium = MockChromium()

    async def start(self) -> Self:
        return self

    async def stop(self) -> None:
        return

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(self, *args) -> None:
        return


class MockBrowserManager:
    """
    Test double for search.services.browser_service.BrowserManager that
    hands out mock contexts instead of launching a real browser.
    """

    def __init__(self, idle_timeout: float | None = None) -> None:
        self.idle_timeout = idle_timeout
        self.contexts = 0
        self.shutdowns = 0

    async def new_context(
        self, default_timeout_ms: float | None = None
    ) -> MockContext:
        self.contexts += 1
        return MockContext()

    async def shutdown(self) -> None:
        self.shutdowns += 1
