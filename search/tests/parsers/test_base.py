from django.test import TestCase

from search.parsers.base import AbstractParser, Parser
from search.parsers.bs4_parser import BeautifulSoupParser
from search.parsers.playwright_parser import PlaywrightParser


class TestParser(TestCase):
    async def test_parser_bs4(self):
        async with Parser("bs4") as parser:
            self.assertEqual(parser.name(), "bs4")
            self.assertIsInstance(parser, BeautifulSoupParser)
            self.assertIsInstance(parser, AbstractParser)

    async def test_parser_playwright(self):
        async with Parser("playwright") as parser:
            self.assertEqual(parser.name(), "playwright")
            self.assertIsInstance(parser, PlaywrightParser)
            self.assertIsInstance(parser, AbstractParser)

    async def test_parser_instance_invalid(self):
        with self.assertRaises(ValueError):
            async with Parser("invalid") as _:
                pass