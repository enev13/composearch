from abc import ABC, abstractmethod
from typing import Any

from asgiref.sync import sync_to_async
from bs4 import BeautifulSoup
from playwright.async_api import async_playwright


class AbstractParser(ABC):
    _name = None

    @abstractmethod
    async def __aenter__(self):
        raise NotImplementedError

    @abstractmethod
    async def __aexit__(self, *args: Any):
        raise NotImplementedError

    @classmethod
    def name(cls) -> str:
        return cls._name

    @abstractmethod
    async def load_content(self, html_content: str) -> None:
        raise NotImplementedError

    @abstractmethod
    async def select_element(self, selector: str, type: str, **kwargs) -> str | None:
        raise NotImplementedError


class Parser(AbstractParser):
    def __init__(self, parser: str) -> None:
        self.parser_type = parser
        self.parser = None

    async def identify_parser(self):
        for parser in AbstractParser.__subclasses__():
            try:
                if parser.name() == self.parser_type:
                    return parser()
            except Exception:
                continue
        raise ValueError(f"Parser {self.parser_type} not found")

    async def __aenter__(self):
        if not self.parser:
            self.parser = await self.identify_parser()
            await self.parser.__aenter__()
        return self

    async def __aexit__(self, *args: Any):
        await self.parser.__aexit__(*args)
        self.parser = None

    async def load_content(self, html_content: str) -> None:
        return await self.parser.load_content(html_content)

    async def select_element(self, selector: str, type: str, **kwargs) -> str | None:
        return await self.parser.select_element(selector, type, **kwargs)


class BeautifulSoupParser(AbstractParser):
    _name = "bs4"

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args: Any):
        pass

    async def load_content(self, html_content: str) -> None:
        self.soup = await sync_to_async(BeautifulSoup)(html_content, "html.parser")

    async def select_element(self, selector: str, type: str) -> str | None:
        element = await sync_to_async(self.soup.select_one)(selector)
        if element:
            if type == "text":
                return await sync_to_async(element.text.strip)()
            elif type == "href":
                return await sync_to_async(element.get)("href")
            elif type == "src":
                return await sync_to_async(element.get)("src")


class PlaywrightParser(AbstractParser):
    _name = "playwright"

    async def __aenter__(self):
        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch()
        return self

    async def __aexit__(self, *args: Any):
        await self.browser.close()
        await self.playwright.stop()

    async def load_content(self, html_content: str) -> None:
        self.html_content = html_content

    async def select_element(self, selector: str, type: str) -> str | None:
        page = await self.browser.new_page()
        await page.set_content(self.html_content)
        element = page.locator(selector).first
        if element:
            if type == "text":
                return await element.inner_text()
            elif type == "href":
                return await element.get_attribute("href")
            elif type == "src":
                return await element.get_attribute("src")
