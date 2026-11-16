from decimal import Decimal
from unittest import TestCase

from search.utils.helpers import to_decimal


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

    def test_to_decimal_multi_digit_decimals(self):
        # a separator followed by more than 3 digits is a decimal point,
        # not a thousands separator (e.g. "4.98000 EUR" -> 4.98)
        self.assertEqual(to_decimal("4.98000 EUR"), Decimal("4.98000"))
        self.assertEqual(to_decimal("124.00000 EUR"), Decimal("124.00000"))
        self.assertEqual(to_decimal("3.50208 USD"), Decimal("3.50208"))
        self.assertEqual(to_decimal("1 234,56 \u20ac"), Decimal("1234.56"))