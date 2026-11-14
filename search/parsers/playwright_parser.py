from typing import Self

from playwright.async_api import Browser, BrowserContext, Playwright, async_playwright

from search.parsers.base import AbstractParser


class PlaywrightParser(AbstractParser):
    _name = "playwright"

    async def __aenter__(self) -> Self:
        self.playwright: Playwright = await async_playwright().start()
        self.browser: Browser = await self.playwright.chromium.launch()
        self.context: BrowserContext = await self.browser.new_context()
        return self

    async def __aexit__(self, *args: object) -> None:
        await self.context.close()
        await self.browser.close()
        await self.playwright.stop()

    async def load_content(self, html_content: str) -> None:
        self.html_content: str = html_content

    async def select_element(self, selector: str, type: str) -> str | None:
        page = await self.context.new_page()
        await page.set_content(self.html_content)
        element = await page.query_selector(selector)
        if element:
            if type == "text":
                # Get text content excluding strikethrough price spans
                js_code = '''el => {
                    const clone = el.cloneNode(true);
                    const strikethrough = clone.querySelector("span.streichpreis");
                    if (strikethrough) strikethrough.remove();
                    return clone.innerText.trim();
                }'''
                return await element.evaluate(js_code)
            elif type == "href":
                return await element.get_attribute("href")
            elif type == "src":
                return await element.get_attribute("src")
            else:
                raise ValueError(f"Type {type} not supported")
        await page.close()
        return None
