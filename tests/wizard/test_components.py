"""Tests for the component-level prompts (volume + preset)."""

from __future__ import annotations

from decimal import Decimal
from typing import TYPE_CHECKING

from mixsheet.domain.project import (
    AreaHeightVolume,
    DimensionsVolume,
    DirectVolume,
)
from mixsheet.wizard.components import prompt_preset, prompt_volume

if TYPE_CHECKING:
    from collections.abc import Callable
    from io import StringIO

    from rich.console import Console

    from mixsheet.domain import Catalog


def test_prompt_volume_dimensions_returns_decimals(
    make_console: Callable[[str], tuple[Console, StringIO]],
) -> None:
    console, _ = make_console("dimensions\n800\n400\n120\n")
    volume = prompt_volume(console)
    assert isinstance(volume, DimensionsVolume)
    assert volume.length_mm == Decimal("800")
    assert volume.width_mm == Decimal("400")
    assert volume.height_mm == Decimal("120")
    assert volume.volume_l == Decimal("38.4")


def test_prompt_volume_area_height(
    make_console: Callable[[str], tuple[Console, StringIO]],
) -> None:
    console, _ = make_console("area_height\n240000\n80\n")
    volume = prompt_volume(console)
    assert isinstance(volume, AreaHeightVolume)
    assert volume.volume_l == Decimal("19.2")


def test_prompt_volume_direct(
    make_console: Callable[[str], tuple[Console, StringIO]],
) -> None:
    console, _ = make_console("direct\n12.5\n")
    volume = prompt_volume(console)
    assert isinstance(volume, DirectVolume)
    assert volume.volume_l == Decimal("12.5")


def test_prompt_volume_below_min_decline_re_prompts_mode(
    make_console: Callable[[str], tuple[Console, StringIO]],
) -> None:
    # 50 x 20 x 5 = 5000 mm3 = 0.005 L → below 0.01 L threshold
    # Decline 'continue?' (n) → loops back to mode prompt
    # Pick direct mode with 1 L → accepts
    console, out = make_console("dimensions\n50\n20\n5\nn\ndirect\n1\n")
    volume = prompt_volume(console)
    assert isinstance(volume, DirectVolume)
    assert volume.volume_l == Decimal("1")
    assert "below the minimum useful volume" in out.getvalue()


def test_prompt_volume_below_min_accept_proceeds(
    make_console: Callable[[str], tuple[Console, StringIO]],
) -> None:
    console, _ = make_console("dimensions\n50\n20\n5\ny\n")
    volume = prompt_volume(console)
    assert volume.volume_l == Decimal("0.005")


def test_prompt_volume_zero_dimension_re_prompts(
    make_console: Callable[[str], tuple[Console, StringIO]],
) -> None:
    console, out = make_console("dimensions\n0\n100\n100\n100\n")
    # ask_decimal with minimum=0 enforces > 0; rejects "0" then takes 100/100/100
    volume = prompt_volume(console)
    assert isinstance(volume, DimensionsVolume)
    assert volume.length_mm == Decimal("100")
    assert "Length must be > 0. (mixsheet help volume)" in out.getvalue()


def test_prompt_preset_pins_catalog_version(
    make_console: Callable[[str], tuple[Console, StringIO]],
    catalog: Catalog,
) -> None:
    console, out = make_console("1\n")
    preset_id, preset_version = prompt_preset(console, catalog)
    assert preset_id == catalog.presets[0].id
    assert preset_version == catalog.presets[0].version
    rendered = out.getvalue()
    for preset in catalog.presets:
        assert preset.name in rendered


def test_prompt_preset_shows_density_and_application(
    make_console: Callable[[str], tuple[Console, StringIO]],
    catalog: Catalog,
) -> None:
    console, out = make_console("1\n")
    prompt_preset(console, catalog)
    rendered = out.getvalue()
    first = catalog.presets[0]
    assert f"({first.density_kg_per_l} kg/L)" in rendered
    assert (first.application or first.description or "") in rendered
