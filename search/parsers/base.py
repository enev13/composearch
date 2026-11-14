import logging
from abc import ABC, abstractmethod
from typing import Any

log = logging.getLogger(__name__)


class AbstractParser(ABC):
    _name: str = ""

    @abstractmethod
    async def __aenter__(self) -> "AbstractParser":
        raise NotImplementedError

    @abstractmethod
    async def __aexit__(self, *args: object) -> None:
        raise NotImplementedError

    @classmethod
    def name(cls) -> str:
        return cls._name

    @abstractmethod
    async def load_content(self, html_content: str) -> None:
        raise NotImplementedError

    @abstractmethod
    async def select_element(self, selector: str, type: str, **kwargs: Any) -> str | None:
        raise NotImplementedError


class Parser(AbstractParser):
    def __init__(self, parser: str) -> None:
        self.parser_type: str = parser

    async def identify_parser(self) -> "AbstractParser":
        for parser in AbstractParser.__subclasses__():
            try:
                if parser.name() == self.parser_type:
                    return parser()
            except Exception:
                log.debug(f"Skipping parser {parser.__name__}", exc_info=True)
                continue
        raise ValueError(f"Parser {self.parser_type} not found")

    async def __aenter__(self) -> "AbstractParser":
        self.parser: AbstractParser = await self.identify_parser()
        await self.parser.__aenter__()
        return self.parser

    async def __aexit__(self, *args: object) -> None:
        await self.parser.__aexit__(*args)

    async def load_content(self, html_content: str) -> None:
        ...

    async def select_element(self, selector: str, type: str, **kwargs: Any) -> str | None:
        ...
