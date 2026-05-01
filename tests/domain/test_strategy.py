"""Strategy enum."""

from __future__ import annotations

import pytest

from mixsheet.domain import Strategy


def test_round_trips_a_known_strategy() -> None:
    value = Strategy("minimal_waste")
    assert value is Strategy.MINIMAL_WASTE
    assert str(value) == "minimal_waste"


def test_rejects_an_unknown_strategy() -> None:
    with pytest.raises(ValueError, match="greedy"):
        Strategy("greedy")


def test_exposes_only_documented_members() -> None:
    assert {member.value for member in Strategy} == {
        "cheapest",
        "bulk_value",
        "minimal_waste",
    }
