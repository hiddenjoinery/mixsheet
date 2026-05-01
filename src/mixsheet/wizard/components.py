"""Component-level prompts: volume input, preset pick, full component build.

These helpers are split from :mod:`mixsheet.wizard.prompts` because they
compose multiple prompts and validate against domain models.
"""

from __future__ import annotations

import re
from decimal import Decimal
from typing import TYPE_CHECKING

from pydantic import ValidationError

from mixsheet.domain.project import (
    AreaHeightVolume,
    Component,
    DimensionsVolume,
    DirectVolume,
    Volume,
)
from mixsheet.wizard import prompts

if TYPE_CHECKING:
    from rich.console import Console

    from mixsheet.domain.catalog import Catalog

MIN_USEFUL_VOLUME_L = Decimal("0.01")
_ID_INVALID = re.compile(r"[^a-z0-9-]+")
_ID_DASHES = re.compile(r"-+")


def _id_from_name(name: str) -> str:
    lowered = name.strip().lower().replace(" ", "-")
    cleaned = _ID_INVALID.sub("", lowered)
    return _ID_DASHES.sub("-", cleaned).strip("-") or "component"


def _prompt_dimensions(console: Console) -> DimensionsVolume:
    while True:
        length = prompts.ask_decimal(
            console,
            "? Length (mm)",
            minimum=Decimal("0"),
            help_key="volume",
            field_label="Length",
        )
        width = prompts.ask_decimal(
            console,
            "? Width (mm)",
            minimum=Decimal("0"),
            help_key="volume",
            field_label="Width",
        )
        height = prompts.ask_decimal(
            console,
            "? Height (mm)",
            minimum=Decimal("0"),
            help_key="volume",
            field_label="Height",
        )
        try:
            return DimensionsVolume(length_mm=length, width_mm=width, height_mm=height)
        except ValidationError as exc:
            _print_volume_errors(console, exc)


def _prompt_area_height(console: Console) -> AreaHeightVolume:
    while True:
        area = prompts.ask_decimal(
            console,
            "? Area (mm²)",
            minimum=Decimal("0"),
            help_key="volume",
            field_label="Area",
        )
        height = prompts.ask_decimal(
            console,
            "? Height (mm)",
            minimum=Decimal("0"),
            help_key="volume",
            field_label="Height",
        )
        try:
            return AreaHeightVolume(area_mm2=area, height_mm=height)
        except ValidationError as exc:
            _print_volume_errors(console, exc)


def _prompt_direct(console: Console) -> DirectVolume:
    while True:
        volume_l = prompts.ask_decimal(
            console,
            "? Volume (L)",
            minimum=Decimal("0"),
            help_key="volume",
            field_label="Volume",
        )
        try:
            return DirectVolume(volume_l=volume_l)
        except ValidationError as exc:
            _print_volume_errors(console, exc)


def _print_volume_errors(console: Console, exc: ValidationError) -> None:
    for err in exc.errors():
        loc = ".".join(str(part) for part in err["loc"]) or "value"
        console.print(f"  ! {loc} must be > 0. (mixsheet help volume)")


def prompt_volume(console: Console) -> Volume:
    """Prompt for one of the three volume modes and return a validated ``Volume``.

    Loops on the below-minimum confirmation: declining the
    "continue anyway?" prompt returns to mode selection so the user
    can re-enter dimensions.
    """
    while True:
        mode = prompts.ask_choice(
            console,
            "? How do you know the volume?",
            ["dimensions", "area_height", "direct"],
            help_key="volume",
            default="dimensions",
        )
        if mode == "dimensions":
            volume: Volume = _prompt_dimensions(console)
        elif mode == "area_height":
            volume = _prompt_area_height(console)
        else:
            volume = _prompt_direct(console)

        if volume.volume_l < MIN_USEFUL_VOLUME_L:
            console.print(
                f"  ! Computed volume {volume.volume_l} L is below the minimum"
                f" useful volume ({MIN_USEFUL_VOLUME_L} L).",
            )
            if not prompts.ask_yes_no(
                console,
                "? Continue anyway?",
                help_key="volume",
                default=False,
            ):
                continue
        return volume


def prompt_preset(console: Console, catalog: Catalog) -> tuple[str, str]:
    """Pick a mix preset and return ``(preset_id, preset_version)`` pinned now."""
    options = []
    for preset in catalog.presets:
        application = preset.application or preset.description or ""
        suffix = f" — {application}" if application else ""
        label = f"{preset.name} ({preset.density_kg_per_l} kg/L){suffix}"
        options.append((preset.id, label))
    chosen_id = prompts.ask_indexed_choice(
        console,
        "? Mix preset",
        options,
        help_key="preset",
    )
    preset = catalog.preset_by_id(chosen_id)
    assert preset is not None  # noqa: S101 - id came from the same catalog
    return preset.id, preset.version


def prompt_component(
    console: Console,
    catalog: Catalog,
    *,
    component_index: int,
) -> Component:
    """Prompt for a fresh ``Component`` (name, quantity, volume, preset)."""
    name = prompts.ask_text(
        console,
        "? Component name",
        help_key="component_name",
    )
    quantity = prompts.ask_int(
        console,
        "? Quantity",
        minimum=1,
        help_key="quantity",
        default=1,
        field_label="Quantity",
    )
    volume = prompt_volume(console)
    preset_id, preset_version = prompt_preset(console, catalog)

    base_id = _id_from_name(name)
    component_id = base_id if component_index == 0 else f"{base_id}-{component_index + 1}"
    return Component(
        id=component_id,
        name=name,
        quantity=quantity,
        volume=volume,
        preset_id=preset_id,
        preset_version=preset_version,
    )
