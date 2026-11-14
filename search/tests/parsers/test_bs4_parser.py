from django.test import TestCase

from search.parsers.base import AbstractParser, Parser
from search.parsers.bs4_parser import BeautifulSoupParser


class TestBeautifulSoupParser(TestCase):
    async def test_beautifulsoup_parser(self):
        async with BeautifulSoupParser() as parser:
            self.assertEqual(parser.name(), "bs4")
            self.assertIsInstance(parser, AbstractParser)

    # Load content
    async def test_parser_bs4_load_content(self):
        async with Parser("bs4") as parser:
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

    # Select element of invalid type
    async def test_parser_bs4_select_invalid_element_type(self):
        async with Parser("bs4") as parser:
            await parser.load_content(
                '<html><a href="https://example.com">link</a><img src="https://example.com/img.jpg"></html>'
            )
            with self.assertRaises(ValueError):
                await parser.select_element("a", "invalid")

    # Select element with strikethrough price - should exclude strikethrough span
    async def test_parser_bs4_select_element_with_strikethrough(self):
        async with Parser("bs4") as parser:
            html = '''
            <html><body><table><tr>
            <td class="price">
                <div>
                    <span class="rabatt u5p"> </span>
                    64,58 EUR <span class="streichpreis">67,23 EUR</span>
                </div>
            </td>
            </tr></table></body></html>
            '''
            await parser.load_content(html)
            result = await parser.select_element("td.price > div", "text")
            self.assertEqual(result, "64,58 EUR")
            # Should not include strikethrough price
            self.assertNotIn("67,23 EUR", result)

    # Select element without strikethrough price - should work normally
    async def test_parser_bs4_select_element_without_strikethrough(self):
        async with Parser("bs4") as parser:
            html = '''
            <html><body><table><tr>
            <td class="price">
                <div>25,40 EUR</div>
            </td>
            </tr></table></body></html>
            '''
            await parser.load_content(html)
            result = await parser.select_element("td.price > div", "text")
            self.assertEqual(result, "25,40 EUR")