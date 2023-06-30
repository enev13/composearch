import asyncio
from typing import Any

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
        await asyncio.sleep(CONTENT_TIME)
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
