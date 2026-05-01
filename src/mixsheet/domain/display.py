"""Display-precision constants shared by every renderer.

Formatting helpers belong with the wizard, where Rich rendering needs
are concrete. This module exposes only the precision rules from
FR-012 so wizard, exports, and tests pull them from one place.
"""

from __future__ import annotations

from decimal import Decimal

QUANTITY_DECIMALS_LOW: int = 1
"""Decimal places for quantities at or below ``QUANTITY_THRESHOLD``."""

QUANTITY_DECIMALS_HIGH: int = 0
"""Decimal places for quantities strictly above ``QUANTITY_THRESHOLD``."""

QUANTITY_THRESHOLD: Decimal = Decimal("10")
"""Threshold (in display units) at which quantity precision switches."""

PRICE_DECIMALS: int = 2
"""Decimal places for monetary values."""

PERCENT_DECIMALS: int = 0
"""Decimal places for percentage values."""
