from decimal import Decimal
from unittest import TestCase

from search.helpers import to_decimal


class TestToDecimal(TestCase):
    def test_to_decimal(self):
        self.assertEqual(to_decimal("1.23"), Decimal("1.23"))
        self.assertEqual(to_decimal("1,23"), Decimal("1.23"))
        self.assertEqual(to_decimal(" -1.23"), Decimal("-1.23"))
        self.assertEqual(to_decimal("1 234.56"), Decimal("1234.56"))
        self.assertEqual(to_decimal("1,234.56"), Decimal("1234.56"))
        self.assertEqual(to_decimal("1"), Decimal("1.0"))
        self.assertEqual(to_decimal("1.23abc"), Decimal("1.23"))
        self.assertEqual(to_decimal("Price: 1.23 EUR"), Decimal("1.23"))
        self.assertEqual(to_decimal("1.234.56"), Decimal("1234.56"))
        self.assertEqual(to_decimal("not a float"), None)
