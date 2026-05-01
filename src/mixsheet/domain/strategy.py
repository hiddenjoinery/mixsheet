"""Purchase-list strategy enum.

The optimizer (lands in ``add-purchase-optimizer``) consumes this enum.
This module owns the names and string values only.
"""

from __future__ import annotations

from enum import StrEnum


class Strategy(StrEnum):
    """Picking strategy for the purchase optimizer."""

    CHEAPEST = "cheapest"
    BULK_VALUE = "bulk_value"
    MINIMAL_WASTE = "minimal_waste"
