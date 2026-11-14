from typing import Self

from asgiref.sync import sync_to_async
from bs4 import BeautifulSoup

from search.parsers.base import AbstractParser


class BeautifulSoupParser(AbstractParser):
    _name = "bs4"

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(self, *args: object) -> None:
        pass

    @sync_to_async
    def load_content(self, html_content: str) -> None:
        self.soup: BeautifulSoup = BeautifulSoup(html_content, "html.parser")

    @sync_to_async
    def select_element(self, selector: str, type: str) -> str | None:
        element = self.soup.select_one(selector)
        if element:
            if type == "text":
                # Clone the element to avoid modifying the original
                clone = element.__copy__()
                # Remove strikethrough price spans to avoid extracting both prices
                for strikethrough in clone.find_all('span', class_='streichpreis'):
                    strikethrough.decompose()
                return clone.text.strip()
            elif type == "href":
                return element.get("href")
            elif type == "src":
                return element.get("src")
            else:
                raise ValueError(f"Type {type} not supported")
