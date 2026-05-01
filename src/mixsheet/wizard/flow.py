"""Shared sub-flows used by both ``mixsheet new`` and ``mixsheet open``.

The wizard files glue prompts together; the actual stepwise pipeline
(overage → strategy → optimise → export) lives here so both entry
points share the same behaviour and the save-after-each-prompt
invariant is guaranteed in one place.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from mixsheet.domain.aggregator import aggregate_project
from mixsheet.domain.mixsheet_renderer import render_component_mixsheet
from mixsheet.domain.optimizer import (
    UnpurchasableMaterialError,
    optimize_purchase,
)
from mixsheet.domain.project import save_project
from mixsheet.domain.renderer import render_purchase_list
from mixsheet.domain.strategy import Strategy
from mixsheet.export.excel import (
    MissingExcelExtraError,
    ProjectHeader,
    write_mixsheet_workbook,
    write_purchase_workbook,
)
from mixsheet.wizard import display, prompts
from mixsheet.wizard.comparison import build_comparison_table

if TYPE_CHECKING:
    from pathlib import Path

    from rich.console import Console

    from mixsheet.domain.catalog import Catalog
    from mixsheet.domain.optimizer import PurchaseList
    from mixsheet.domain.project import Project
    from mixsheet.wizard.paths import ProjectPaths

OVERAGE_DEFAULT_PERCENT = 10
PERCENT = Decimal("100")


def _update_purchase(project: Project, **changes: object) -> Project:
    new_purchase = project.purchase.model_copy(update=changes)
    return project.model_copy(update={"purchase": new_purchase})


def prompt_overage(console: Console, project: Project, project_file: Path) -> Project:
    """Prompt for the integer overage percent and persist it."""
    current = int((project.purchase.overage_pct * PERCENT).to_integral_value())
    percent = prompts.ask_int(
        console,
        "? Project overage (% extra applied to purchase)",
        minimum=0,
        help_key="overage",
        default=current or OVERAGE_DEFAULT_PERCENT,
        field_label="Overage",
    )
    updated = _update_purchase(project, overage_pct=Decimal(percent) / PERCENT)
    return save_project(updated, project_file)


def maybe_show_comparison(
    console: Console,
    project: Project,
    catalog: Catalog,
    *,
    no_compare: bool,
) -> None:
    """Show the strategy comparison table unless suppressed."""
    if no_compare:
        return
    if not prompts.ask_yes_no(
        console,
        "? Strategy comparison?",
        help_key="strategies",
        default=True,
    ):
        return
    with console.status("Comparing strategies..."):
        comparison = build_comparison_table(project, catalog)
    display.show_strategy_comparison(console, comparison)


def prompt_strategy(console: Console, project: Project, project_file: Path) -> Project:
    """Prompt for the optimiser strategy and persist it."""
    options = [(strategy.value, strategy.value) for strategy in Strategy]
    chosen = prompts.ask_indexed_choice(
        console,
        "? Choose strategy",
        options,
        help_key="strategies",
    )
    updated = _update_purchase(project, strategy=Strategy(chosen))
    return save_project(updated, project_file)


def run_optimizer_with_recovery(
    console: Console,
    project: Project,
    catalog: Catalog,
    project_file: Path,
) -> tuple[Project, PurchaseList] | None:
    """Run the optimiser, prompting for excluded-material remediation.

    Returns ``(project, purchase_list)`` on success or ``None`` if the
    user quits during remediation. The project is re-saved when the
    user adds a material to ``excluded_materials``.
    """
    while True:
        breakdown = aggregate_project(project, catalog)
        try:
            purchase_list = optimize_purchase(
                breakdown,
                catalog,
                strategy=project.purchase.strategy,
                overage_pct=project.purchase.overage_pct,
                excluded_materials=project.purchase.excluded_materials,
            )
        except UnpurchasableMaterialError as exc:
            console.print(
                f"  ! No package available for material {exc.material_id!r}.",
            )
            choice = prompts.ask_choice(
                console,
                "? How to handle?",
                ["skip", "exclude", "quit"],
                help_key="purchase",
                default="exclude",
            )
            if choice == "quit":
                return None
            new_excluded = [*project.purchase.excluded_materials, exc.material_id]
            project = _update_purchase(project, excluded_materials=new_excluded)
            project = save_project(project, project_file)
            continue
        return project, purchase_list


def export_artifacts(
    console: Console,
    project: Project,
    catalog: Catalog,
    purchase_list: PurchaseList,
    paths: ProjectPaths,
) -> bool:
    """Render and write both workbooks. Return ``True`` on success."""
    breakdown = aggregate_project(project, catalog)
    purchase_view = render_purchase_list(purchase_list)
    component_views = [
        render_component_mixsheet(
            component_breakdown,
            component_name=next(
                component.name
                for component in project.components
                if component.id == component_breakdown.component_id
            ),
        )
        for component_breakdown in breakdown.components
    ]

    overage_display = f"{int((project.purchase.overage_pct * PERCENT).to_integral_value())}%"
    header = ProjectHeader(
        project_name=project.name,
        generation_date=datetime.now(tz=project.updated_at.tzinfo).isoformat(),
        strategy=project.purchase.strategy.value,
        overage_display=overage_display,
    )

    paths.purchase_xlsx.parent.mkdir(parents=True, exist_ok=True)
    paths.mixsheet_xlsx.parent.mkdir(parents=True, exist_ok=True)
    try:
        write_purchase_workbook(purchase_view, header, paths.purchase_xlsx)
        write_mixsheet_workbook(component_views, header, paths.mixsheet_xlsx)
    except MissingExcelExtraError as exc:
        console.print(f"  ! {exc}", markup=False)
        return False

    display.show_aggregated_breakdown(console, breakdown.components)
    display.show_purchase_list(console, purchase_view)
    console.print()
    console.print("— Project saved —")
    console.print(f"  Mix sheets:    {paths.mixsheet_xlsx}")
    console.print(f"  Purchase list: {paths.purchase_xlsx}")
    console.print(f"  Project file:  {paths.project_file}")
    return True


def finalize(
    console: Console,
    project: Project,
    catalog: Catalog,
    paths: ProjectPaths,
    *,
    no_compare: bool,
) -> bool:
    """Run the overage → strategy → optimise → export tail end.

    Returns ``True`` when both workbooks are written, ``False`` if the
    user quits the unpurchasable-material remediation or the export
    extra is missing.
    """
    project = prompt_overage(console, project, paths.project_file)
    maybe_show_comparison(console, project, catalog, no_compare=no_compare)
    project = prompt_strategy(console, project, paths.project_file)
    result = run_optimizer_with_recovery(console, project, catalog, paths.project_file)
    if result is None:
        return False
    project, purchase_list = result
    return export_artifacts(console, project, catalog, purchase_list, paths)
