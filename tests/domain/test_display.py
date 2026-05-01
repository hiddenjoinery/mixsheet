"""Display-precision constants."""

from __future__ import annotations

from decimal import Decimal

from mixsheet.domain import (
    PERCENT_DECIMALS,
    PRICE_DECIMALS,
    QUANTITY_DECIMALS_HIGH,
    QUANTITY_DECIMALS_LOW,
    QUANTITY_THRESHOLD,
)


def test_constants_take_documented_values() -> None:
    assert QUANTITY_DECIMALS_LOW == 1
    assert QUANTITY_DECIMALS_HIGH == 0
    assert Decimal("10") == QUANTITY_THRESHOLD
    assert PRICE_DECIMALS == 2
    assert PERCENT_DECIMALS == 0
