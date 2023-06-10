from django.test import TestCase
from search.parser import Parser, AbstractParser, BeautifulSoupParser, PlaywrightParser


class TestParser(TestCase):
    async def test_beautifulsoup_parser(self):
        async with BeautifulSoupParser() as parser:
            self.assertEqual(parser.name(), "bs4")
            self.assertIsInstance(parser, AbstractParser)

    async def test_playwright_parser(self):
        async with PlaywrightParser() as parser:
            self.assertEqual(parser.name(), "playwright")
            self.assertIsInstance(parser, AbstractParser)

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

    # Load content
    async def test_parser_bs4_load_content(self):
        async with Parser("bs4") as parser:
            await parser.load_content("<html></html>")
            # self.assertEqual(parser.content, "<html></html>")

    async def test_parser_playwright_load_content(self):
        async with Parser("playwright") as parser:
            await parser.load_content("<html></html>")
            # self.assertEqual(parser.content, "<html></html>")

    # Select element
    async def test_parser_bs4_select_element(self):
        # select text, href, src, elements
        async with Parser("bs4") as parser:
            await parser.load_content(
                '<html><a href="https://example.com">link</a><img src="https://example.com/img.jpg"></html>'
            )
            self.assertEqual(await parser.select_element("a", "text"), "link")
            self.assertEqual(await parser.select_element("a", "href"), "https://example.com")
            self.assertEqual(await parser.select_element("img", "src"), "https://example.com/img.jpg")

    async def test_parser_playwright_select_element(self):
        async with Parser("playwright") as parser:
            await parser.load_content(
                '<html><a href="https://example.com">link</a><img src="https://example.com/img.jpg"></html>'
            )
            self.assertEqual(await parser.select_element("a", "text"), "link")
            self.assertEqual(await parser.select_element("a", "href"), "https://example.com")
            self.assertEqual(await parser.select_element("img", "src"), "https://example.com/img.jpg")

    # Select element of invalid type
    async def test_parser_bs4_select_invalid_element_type(self):
        async with Parser("bs4") as parser:
            await parser.load_content(
                '<html><a href="https://example.com">link</a><img src="https://example.com/img.jpg"></html>'
            )
            with self.assertRaises(ValueError):
                await parser.select_element("a", "invalid")

    async def test_parser_playwright_select_invalid_element_type(self):
        async with Parser("playwright") as parser:
            await parser.load_content(
                '<html><a href="https://example.com">link</a><img src="https://example.com/img.jpg"></html>'
            )
            with self.assertRaises(ValueError):
                await parser.select_element("a", "invalid")
