"""Resolve project-file and workbook paths for both project shapes.

Single-component projects produce three sibling files
(``<slug>.yaml``, ``<slug>.purchase.xlsx``, ``<slug>.mixsheets.xlsx``).
Machine projects live inside a per-project folder
(``<slug>/project.yaml``, ``<slug>/purchase.xlsx``,
``<slug>/mixsheets.xlsx``). The layout follows
``docs/user-flow.md`` and is the single concern of this module — the
wizard never builds paths inline.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict

DEFAULT_PROJECT_DIR = Path("./projects")
SLUG_FALLBACK = "project"
_SLUG_INVALID = re.compile(r"[^a-z0-9-]+")
_SLUG_DASHES = re.compile(r"-+")


class ProjectPaths(BaseModel):
    """Three resolved filesystem paths for one project."""

    model_config = ConfigDict(frozen=True, arbitrary_types_allowed=True)

    project_file: Path
    purchase_xlsx: Path
    mixsheet_xlsx: Path


def slugify(name: str) -> str:
    """Return a lowercase, dash-separated slug fit for filesystem paths.

    Strips characters outside ``[a-z0-9-]``, collapses whitespace and
    runs of dashes, and falls back to ``"project"`` for an empty result
    so a path is always producible.
    """
    lowered = name.strip().lower()
    dashed = lowered.replace(" ", "-")
    cleaned = _SLUG_INVALID.sub("", dashed)
    collapsed = _SLUG_DASHES.sub("-", cleaned).strip("-")
    return collapsed or SLUG_FALLBACK


def resolve_new_paths(
    name: str,
    shape: Literal["single", "machine"],
    project_dir: Path | None = None,
) -> ProjectPaths:
    """Compute the three project paths for a freshly named project.

    ``project_dir`` defaults to ``./projects`` and is resolved relative
    to the current working directory. The returned paths are not
    created on disk; the caller is responsible for ``mkdir``.
    """
    base = (project_dir or DEFAULT_PROJECT_DIR).resolve()
    slug = slugify(name)
    if shape == "single":
        return ProjectPaths(
            project_file=base / f"{slug}.yaml",
            purchase_xlsx=base / f"{slug}.purchase.xlsx",
            mixsheet_xlsx=base / f"{slug}.mixsheets.xlsx",
        )
    folder = base / slug
    return ProjectPaths(
        project_file=folder / "project.yaml",
        purchase_xlsx=folder / "purchase.xlsx",
        mixsheet_xlsx=folder / "mixsheets.xlsx",
    )


def resolve_open_paths(project_path: Path) -> ProjectPaths:
    """Compute the workbook paths siblings of an existing project file.

    The shape is inferred from the file name: ``project.yaml`` inside
    a folder maps to the machine layout, otherwise the flat layout
    sibling to ``<slug>.yaml`` is used.
    """
    resolved = project_path.resolve()
    parent = resolved.parent
    if resolved.name == "project.yaml":
        return ProjectPaths(
            project_file=resolved,
            purchase_xlsx=parent / "purchase.xlsx",
            mixsheet_xlsx=parent / "mixsheets.xlsx",
        )
    stem = resolved.stem
    return ProjectPaths(
        project_file=resolved,
        purchase_xlsx=parent / f"{stem}.purchase.xlsx",
        mixsheet_xlsx=parent / f"{stem}.mixsheets.xlsx",
    )
