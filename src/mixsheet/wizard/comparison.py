"""Strategy comparison: run the optimiser per strategy and tabulate.

The wizard renders the resulting comparison via Rich. The function
itself is pure: it returns frozen rows so tests can assert on the data
without parsing terminal output.
"""

from __future__ import annotations

from decimal import Decimal
from typing import TYPE_CHECKING

from pydantic import BaseModel, ConfigDict, Field

from mixsheet.domain.aggregator import aggregate_project
from mixsheet.domain.optimizer import optimize_purchase
from mixsheet.domain.strategy import Strategy

if TYPE_CHECKING:
    from mixsheet.domain.catalog import Catalog
    from mixsheet.domain.project import Project


class StrategyComparisonRow(BaseModel):
    """One strategy's totals plus tie markers against other strategies."""

    model_config = ConfigDict(frozen=True)

    strategy: Strategy
    total_cost_incl_vat: Decimal
    total_waste_kg: Decimal
    line_count: int = Field(ge=0)
    same_as: list[Strategy]


class StrategyComparison(BaseModel):
    """A frozen comparison table: one row per strategy."""

    model_config = ConfigDict(frozen=True)

    rows: list[StrategyComparisonRow]


def build_comparison_table(project: Project, catalog: Catalog) -> StrategyComparison:
    """Run :func:`optimize_purchase` once per strategy and tabulate.

    The aggregator runs once; only the optimiser repeats. Tie detection
    compares total cost and total waste at full ``Decimal`` precision,
    not their display strings.
    """
    breakdown = aggregate_project(project, catalog)
    overage = project.purchase.overage_pct
    excluded = project.purchase.excluded_materials

    raw_rows: list[tuple[Strategy, Decimal, Decimal, int]] = []
    for strategy in Strategy:
        purchase_list = optimize_purchase(
            breakdown,
            catalog,
            strategy=strategy,
            overage_pct=overage,
            excluded_materials=excluded,
        )
        raw_rows.append(
            (
                strategy,
                purchase_list.total_cost_incl_vat,
                purchase_list.total_waste_kg,
                len(purchase_list.line_items),
            ),
        )

    rows: list[StrategyComparisonRow] = []
    for strategy, cost, waste, line_count in raw_rows:
        same_as = [
            other
            for other, other_cost, other_waste, _ in raw_rows
            if other is not strategy and other_cost == cost and other_waste == waste
        ]
        rows.append(
            StrategyComparisonRow(
                strategy=strategy,
                total_cost_incl_vat=cost,
                total_waste_kg=waste,
                line_count=line_count,
                same_as=same_as,
            ),
        )
    return StrategyComparison(rows=rows)
