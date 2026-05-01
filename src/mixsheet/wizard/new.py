"""``mixsheet new`` flow: collect identity, components, and finalise.

The flow follows :doc:`docs/user-flow.md` golden paths. Every prompt
that mutates project state is followed by a :func:`save_project` call
so a Ctrl-C never loses an answered field once the project file is
created.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from mixsheet.domain.project import new_project, save_project
from mixsheet.wizard import flow, prompts
from mixsheet.wizard.components import prompt_component
from mixsheet.wizard.display import show_volume_summary
from mixsheet.wizard.paths import resolve_new_paths

if TYPE_CHECKING:
    from pathlib import Path

    from rich.console import Console

    from mixsheet.domain.catalog import Catalog


def run_new(  # noqa: PLR0913
    console: Console,
    catalog: Catalog,
    *,
    name: str | None,
    shape: str | None,
    project_dir: Path | None,
    no_compare: bool,
) -> int:
    """Run the ``mixsheet new`` interactive flow.

    Returns the process exit code: ``0`` on full success, ``1`` when
    the user quits remediation or the export extra is missing.
    """
    project_name = name or prompts.ask_text(
        console,
        "? Project name",
        help_key="project_name",
    )
    project_shape_raw = shape or prompts.ask_choice(
        console,
        "? Project shape",
        ["single", "machine"],
        help_key="project_shape",
        default="single",
    )
    if project_shape_raw not in {"single", "machine"}:
        console.print(f"  ! shape must be 'single' or 'machine', got {project_shape_raw!r}.")
        return 1
    project_shape: str = project_shape_raw

    paths = resolve_new_paths(project_name, project_shape, project_dir)  # type: ignore[arg-type]
    paths.project_file.parent.mkdir(parents=True, exist_ok=True)

    first_component = prompt_component(console, catalog, component_index=0)
    show_volume_summary(console, first_component.volume, first_component.quantity)

    project = new_project(
        name=project_name,
        shape=project_shape,  # type: ignore[arg-type]
        components=[first_component],
        catalog=catalog,
    )
    project = save_project(project, paths.project_file)
    console.print(f"— Project saved as {paths.project_file} —")

    if project_shape == "machine":
        index = 1
        while prompts.ask_yes_no(
            console,
            "? Add another component?",
            help_key="add_another",
            default=True,
        ):
            component = prompt_component(console, catalog, component_index=index)
            show_volume_summary(console, component.volume, component.quantity)
            updated_components = [*project.components, component]
            project = project.model_copy(update={"components": updated_components})
            project = save_project(project, paths.project_file)
            index += 1

    success = flow.finalize(
        console,
        project,
        catalog,
        paths,
        no_compare=no_compare,
    )
    return 0 if success else 1
