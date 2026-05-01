"""Project model: components, volume input modes, purchase configuration.

The project file is the unit of work and the unit of resumption. The
wizard mutates :class:`Project` between prompts (so this model is
strict but not frozen); each prompt's answer is written to disk via
:func:`save_project` before the next prompt.
"""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Annotated, Any, Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator

from mixsheet.domain._yaml import safe_load_decimal
from mixsheet.domain.strategy import Strategy

if TYPE_CHECKING:
    from pathlib import Path

    from mixsheet.domain.catalog import Catalog

MM3_PER_LITRE = Decimal("1000000")
SUPPORTED_SCHEMA_VERSION = 1


class _StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class DimensionsVolume(_StrictModel):
    """Volume given by length x width x height (mm)."""

    mode: Literal["dimensions"] = "dimensions"
    length_mm: Decimal = Field(gt=Decimal("0"))
    width_mm: Decimal = Field(gt=Decimal("0"))
    height_mm: Decimal = Field(gt=Decimal("0"))

    @property
    def volume_l(self) -> Decimal:
        """Return litres derived from the rectangular dimensions."""
        return self.length_mm * self.width_mm * self.height_mm / MM3_PER_LITRE


class AreaHeightVolume(_StrictModel):
    """Volume given by 2D area (mm²) extruded by height (mm)."""

    mode: Literal["area_height"] = "area_height"
    area_mm2: Decimal = Field(gt=Decimal("0"))
    height_mm: Decimal = Field(gt=Decimal("0"))

    @property
    def volume_l(self) -> Decimal:
        """Return litres derived from area x height."""
        return self.area_mm2 * self.height_mm / MM3_PER_LITRE


class DirectVolume(_StrictModel):
    """Volume given directly in litres."""

    mode: Literal["direct"] = "direct"
    volume_l: Decimal = Field(gt=Decimal("0"))


Volume = Annotated[
    DimensionsVolume | AreaHeightVolume | DirectVolume,
    Field(discriminator="mode"),
]
"""Discriminated union over the three volume input modes."""


class Component(_StrictModel):
    """A single pourable part within a project."""

    id: str = Field(min_length=1)
    name: str = Field(min_length=1)
    quantity: int = Field(ge=1)
    volume: Volume
    preset_id: str = Field(min_length=1)
    preset_version: str = Field(min_length=1)

    @property
    def net_volume_l(self) -> Decimal:
        """Return litres for this component multiplied by ``quantity``."""
        return self.volume.volume_l * Decimal(self.quantity)


class PurchaseConfig(_StrictModel):
    """Project-level purchase configuration: overage, strategy, exclusions."""

    overage_pct: Decimal = Field(default=Decimal("0.10"), ge=Decimal("0"))
    strategy: Strategy = Strategy.CHEAPEST
    excluded_materials: list[str] = Field(default_factory=list)


class Project(_StrictModel):
    """A unit of work: one or more components plus purchase settings."""

    schema_version: Literal[1] = SUPPORTED_SCHEMA_VERSION
    id: str = Field(min_length=1)
    name: str = Field(min_length=1)
    shape: Literal["single", "machine"]
    created_at: datetime
    updated_at: datetime
    components: list[Component] = Field(min_length=1)
    purchase: PurchaseConfig = Field(default_factory=PurchaseConfig)

    @model_validator(mode="after")
    def _single_shape_has_one_component(self) -> Project:
        if self.shape == "single" and len(self.components) != 1:
            msg = f"shape 'single' requires exactly one component, got {len(self.components)}"
            raise ValueError(msg)
        if self.created_at.tzinfo is None or self.updated_at.tzinfo is None:
            msg = "created_at and updated_at must be timezone-aware"
            raise ValueError(msg)
        return self


class CatalogVersionMismatch(BaseModel):
    """A single component whose pinned preset version differs from the catalog."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    component_id: str
    preset_id: str
    pinned_version: str
    catalog_version: str


class ProjectLoadResult(BaseModel):
    """Result of :func:`load_project`: the project plus any version mismatches."""

    model_config = ConfigDict(frozen=True, arbitrary_types_allowed=True)

    project: Project
    mismatches: list[CatalogVersionMismatch]


class ProjectFileError(ValueError):
    """Raised when a project YAML file cannot be loaded or validated."""


def _flatten_project_payload(raw: dict[str, Any], source: str) -> dict[str, Any]:
    if "schema_version" not in raw:
        msg = f"{source}: missing required field 'schema_version'"
        raise ProjectFileError(msg)
    project_block = raw.get("project")
    if not isinstance(project_block, dict):
        type_name = type(project_block).__name__
        msg = f"{source}: 'project' must be a mapping, got {type_name}"
        raise ProjectFileError(msg)
    return {
        "schema_version": raw["schema_version"],
        **project_block,
        "components": raw.get("components", []),
        "purchase": raw.get("purchase", {}),
    }


def _project_to_payload(project: Project) -> dict[str, Any]:
    full = project.model_dump(mode="json")
    project_block = {
        "id": full["id"],
        "name": full["name"],
        "shape": full["shape"],
        "created_at": full["created_at"],
        "updated_at": full["updated_at"],
    }
    return {
        "schema_version": full["schema_version"],
        "project": project_block,
        "components": full["components"],
        "purchase": full["purchase"],
    }


def _detect_mismatches(
    project: Project,
    catalog: Catalog,
) -> list[CatalogVersionMismatch]:
    mismatches: list[CatalogVersionMismatch] = []
    for component in project.components:
        preset = catalog.preset_by_id(component.preset_id)
        if preset is None:
            continue
        if preset.version != component.preset_version:
            mismatches.append(
                CatalogVersionMismatch(
                    component_id=component.id,
                    preset_id=component.preset_id,
                    pinned_version=component.preset_version,
                    catalog_version=preset.version,
                ),
            )
    return mismatches


def load_project(path: Path, catalog: Catalog) -> ProjectLoadResult:
    """Load a project YAML file and report any catalog version mismatches.

    The loader uses :func:`yaml.safe_load`, validates against
    :class:`Project`, and never mutates the file even when mismatches
    exist.
    """
    text = path.read_text(encoding="utf-8")
    source = str(path)
    try:
        raw = safe_load_decimal(text)
    except yaml.YAMLError as exc:
        msg = f"{source}: YAML parse error: {exc}"
        raise ProjectFileError(msg) from exc
    if not isinstance(raw, dict):
        type_name = type(raw).__name__
        msg = f"{source}: top-level YAML must be a mapping, got {type_name}"
        raise ProjectFileError(msg)

    payload = _flatten_project_payload(raw, source)
    try:
        project = Project.model_validate(payload)
    except ValidationError as exc:
        msg = f"{source}: invalid project file: {exc}"
        raise ProjectFileError(msg) from exc
    mismatches = _detect_mismatches(project, catalog)
    return ProjectLoadResult(project=project, mismatches=mismatches)


def save_project(project: Project, path: Path) -> Project:
    """Persist ``project`` to ``path`` as deterministic YAML.

    ``updated_at`` is replaced with the current UTC time. Derived
    fields (``Volume.volume_l`` for non-direct modes,
    ``Component.net_volume_l``) are not written — Pydantic's
    serialisation already excludes ``@property`` accessors.
    """
    refreshed = project.model_copy(update={"updated_at": datetime.now(UTC)})
    payload = _project_to_payload(refreshed)
    text = yaml.safe_dump(payload, sort_keys=True, default_flow_style=False, allow_unicode=True)
    path.write_text(text, encoding="utf-8")
    return refreshed


def new_project(
    name: str,
    shape: Literal["single", "machine"],
    components: list[Component],
    catalog: Catalog,
) -> Project:
    """Construct a fresh :class:`Project` with default-excluded materials seeded.

    ``purchase.excluded_materials`` is seeded from every catalog
    material whose ``default_excluded`` flag is true. Hand-edited
    project files keep whatever the user wrote — this constructor only
    runs at project creation.
    """
    excluded = sorted(m.id for m in catalog.materials if m.default_excluded)
    now = datetime.now(UTC)
    project_id = name.strip().lower().replace(" ", "-") or "project"
    return Project(
        schema_version=SUPPORTED_SCHEMA_VERSION,
        id=project_id,
        name=name,
        shape=shape,
        created_at=now,
        updated_at=now,
        components=components,
        purchase=PurchaseConfig(excluded_materials=excluded),
    )
