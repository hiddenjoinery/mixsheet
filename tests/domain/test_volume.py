"""Volume discriminated-union variants."""

from __future__ import annotations

from decimal import Decimal

import pytest
from pydantic import TypeAdapter, ValidationError

from mixsheet.domain import (
    AreaHeightVolume,
    DimensionsVolume,
    DirectVolume,
    Volume,
)

_volume_adapter: TypeAdapter[Volume] = TypeAdapter(Volume)


def test_computes_volume_from_rectangular_dimensions() -> None:
    volume = DimensionsVolume(
        length_mm=Decimal("800"),
        width_mm=Decimal("400"),
        height_mm=Decimal("120"),
    )
    assert volume.volume_l == Decimal("38.4")


def test_computes_volume_from_area_and_height() -> None:
    volume = AreaHeightVolume(area_mm2=Decimal("240000"), height_mm=Decimal("80"))
    assert volume.volume_l == Decimal("19.2")


def test_passes_through_a_direct_volume() -> None:
    volume = DirectVolume(volume_l=Decimal("12.5"))
    assert volume.volume_l == Decimal("12.5")


def test_rejects_a_non_positive_dimension() -> None:
    with pytest.raises(ValidationError):
        DimensionsVolume(
            length_mm=Decimal("0"),
            width_mm=Decimal("400"),
            height_mm=Decimal("120"),
        )


def test_rejects_fields_from_another_mode() -> None:
    payload = {
        "mode": "dimensions",
        "length_mm": Decimal("100"),
        "width_mm": Decimal("100"),
        "height_mm": Decimal("100"),
        "area_mm2": Decimal("1000"),
    }
    with pytest.raises(ValidationError):
        _volume_adapter.validate_python(payload)


def test_discriminator_dispatches_by_mode() -> None:
    parsed = _volume_adapter.validate_python(
        {"mode": "direct", "volume_l": Decimal("3.5")},
    )
    assert isinstance(parsed, DirectVolume)
    assert parsed.volume_l == Decimal("3.5")
