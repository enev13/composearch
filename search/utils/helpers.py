"""Helper functions"""

import re
from decimal import Decimal


def to_decimal(text: str) -> Decimal | None:
    """
    Takes a string and returns the first float found in the string.
    If no float is found, returns None.
    """
    pattern = r"[-+]?\d{1,3}(?:([.,\s])\d{3})*([.,]\d+)?"
    match = re.search(pattern, text)
    if match:
        if match.group(1):
            return Decimal(match.group().replace(match.group(1), "", 1).replace(",", "."))
        return Decimal(match.group().replace(",", "."))
    else:
        return None
