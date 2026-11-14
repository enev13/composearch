from search.parsers.base import AbstractParser, Parser
from search.parsers.bs4_parser import BeautifulSoupParser
from search.parsers.playwright_parser import PlaywrightParser

__all__ = ["AbstractParser", "BeautifulSoupParser", "Parser", "PlaywrightParser"]
