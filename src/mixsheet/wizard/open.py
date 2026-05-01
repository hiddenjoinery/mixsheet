"""``mixsheet open`` flow: load, surface mismatches, present resume menu.

Loads the project file via :func:`mixsheet.domain.load_project`, which
already reports preset-version drift. Unknown-preset references are
detected after load (the project model itself does not validate
against the catalog) and remediated per component before the resume
menu is shown. The resume menu is computed from project state plus
on-disk workbook presence, never stored in the project file.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from mixsheet.domain.project import (
    Project,
    ProjectFileError,
    load_project,
    save_project,
)
from mixsheet.wizard import flow, prompts
from mixsheet.wizard.components import prompt_component, prompt_volume
from mixsheet.wizard.display import show_volume_summary
from mixsheet.wizard.paths import resolve_open_paths

if TYPE_CHECKING:
    from pathlib import Path

    from rich.console import Console

    from mixsheet.domain.catalog import Catalog
    from mixsheet.wizard.paths import ProjectPaths


def run_open(
    console: Console,
    catalog: Catalog,
    *,
    project_path: Path,
    no_compare: bool,
) -> int:
    """Run the ``mixsheet open`` flow against an existing project file."""
    paths = resolve_open_paths(project_path)
    if not paths.project_file.exists():
        console.print(f"  ! project file not found: {paths.project_file}")
        return 1

    try:
        load_result = load_project(paths.project_file, catalog)
    except ProjectFileError as exc:
        console.print(f"  ! cannot load project file: {exc}")
        return 1
    project = load_result.project

    project = _remediate_unknown_presets(console, catalog, project, paths)
    if project is None:
        return 1

    for mismatch in _detect_mismatches(project, catalog):
        console.print(
            f"  ! Component {mismatch[0]!r} pinned preset {mismatch[1]!r} version"
            f" {mismatch[2]!r}; catalog ships {mismatch[3]!r}.",
        )

    return _resume_menu_loop(console, catalog, project, paths, no_compare=no_compare)


def _detect_mismatches(
    project: Project,
    catalog: Catalog,
) -> list[tuple[str, str, str, str]]:
    rows: list[tuple[str, str, str, str]] = []
    for component in project.components:
        preset = catalog.preset_by_id(component.preset_id)
        if preset is None:
            continue
        if preset.version != component.preset_version:
            rows.append(
                (component.id, component.preset_id, component.preset_version, preset.version),
            )
    return rows


def _remediate_unknown_presets(
    console: Console,
    catalog: Catalog,
    project: Project,
    paths: ProjectPaths,
) -> Project | None:
    """Replace components whose preset id is absent from the catalog.

    Returns the (possibly updated) project, or ``None`` when the user
    quits — in which case the project file is left untouched.
    """
    affected = [
        component
        for component in project.components
        if catalog.preset_by_id(component.preset_id) is None
    ]
    if not affected:
        return project

    available_ids = sorted(p.id for p in catalog.presets)
    for component in affected:
        console.print(
            f"  ! Component {component.id!r} references unknown preset {component.preset_id!r}.",
        )
        console.print(f"    Available presets: {', '.join(available_ids)}")

    options: list[tuple[str, str]] = [("__quit__", "Quit (do not modify the file)")]
    options.extend((preset_id, preset_id) for preset_id in available_ids)

    new_components = list(project.components)
    for component in affected:
        chosen = prompts.ask_indexed_choice(
            console,
            f"? Replace preset for component {component.id!r}",
            options,
            help_key="preset",
        )
        if chosen == "__quit__":
            return None
        replacement = catalog.preset_by_id(chosen)
        assert replacement is not None  # noqa: S101
        position = next(
            i for i, existing in enumerate(new_components) if existing.id == component.id
        )
        new_components[position] = component.model_copy(
            update={"preset_id": replacement.id, "preset_version": replacement.version},
        )

    updated = project.model_copy(update={"components": new_components})
    return save_project(updated, paths.project_file)


def _next_step_label(paths: ProjectPaths) -> str:
    if paths.purchase_xlsx.exists() and paths.mixsheet_xlsx.exists():
        return "re-export"
    return "purchase strategy"


def _resume_menu_loop(
    console: Console,
    catalog: Catalog,
    project: Project,
    paths: ProjectPaths,
    *,
    no_compare: bool,
) -> int:
    while True:
        next_step = _next_step_label(paths)
        options = [
            ("continue", f"Continue where I left off (next: {next_step})"),
            ("add", "Add a component"),
            ("edit", "Edit a component"),
            ("recalc", "Recalculate purchase list"),
            ("export", "Export"),
            ("quit", "Quit"),
        ]
        choice = prompts.ask_indexed_choice(
            console,
            "? What now?",
            options,
            help_key="resume",
        )
        if choice == "quit":
            return 0
        if choice == "continue":
            success = _continue_action(
                console,
                catalog,
                project,
                paths,
                next_step=next_step,
                no_compare=no_compare,
            )
            return 0 if success else 1
        if choice == "add":
            project = _add_component(console, catalog, project, paths)
            continue
        if choice == "edit":
            project = _edit_component(console, project, paths)
            continue
        if choice in {"recalc", "export"}:
            success = flow.finalize(
                console,
                project,
                catalog,
                paths,
                no_compare=no_compare if choice == "recalc" else True,
            )
            return 0 if success else 1


def _continue_action(  # noqa: PLR0913
    console: Console,
    catalog: Catalog,
    project: Project,
    paths: ProjectPaths,
    *,
    next_step: str,
    no_compare: bool,
) -> bool:
    if next_step == "re-export":
        result = flow.run_optimizer_with_recovery(
            console,
            project,
            catalog,
            paths.project_file,
        )
        if result is None:
            return False
        project, purchase_list = result
        return flow.export_artifacts(console, project, catalog, purchase_list, paths)
    return flow.finalize(
        console,
        project,
        catalog,
        paths,
        no_compare=no_compare,
    )


def _add_component(
    console: Console,
    catalog: Catalog,
    project: Project,
    paths: ProjectPaths,
) -> Project:
    component = prompt_component(
        console,
        catalog,
        component_index=len(project.components),
    )
    show_volume_summary(console, component.volume, component.quantity)
    updated = project.model_copy(
        update={"components": [*project.components, component]},
    )
    return save_project(updated, paths.project_file)


def _edit_component(
    console: Console,
    project: Project,
    paths: ProjectPaths,
) -> Project:
    options = [
        (component.id, f"{component.id} — {component.name}") for component in project.components
    ]
    chosen_id = prompts.ask_indexed_choice(
        console,
        "? Which component?",
        options,
        help_key="component_name",
    )
    new_components = [
        component.model_copy(update={"volume": prompt_volume(console)})
        if component.id == chosen_id
        else component
        for component in project.components
    ]
    updated = project.model_copy(update={"components": new_components})
    return save_project(updated, paths.project_file)
