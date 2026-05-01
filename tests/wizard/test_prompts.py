"""Direct unit tests for prompt helpers and ?-help dispatch."""

from __future__ import annotations

from decimal import Decimal
from typing import TYPE_CHECKING

from mixsheet.wizard import prompts

if TYPE_CHECKING:
    from collections.abc import Callable
    from io import StringIO

    from rich.console import Console

    type MakeConsole = Callable[[str], tuple[Console, StringIO]]


def test_ask_text_returns_trimmed_input(
    make_console: MakeConsole,
) -> None:
    console, _ = make_console("Lathe bed riser\n")
    assert prompts.ask_text(console, "name") == "Lathe bed riser"


def test_ask_text_reprompts_on_empty(
    make_console: MakeConsole,
) -> None:
    console, out = make_console("\nrouter\n")
    assert prompts.ask_text(console, "name") == "router"
    assert "must not be empty" in out.getvalue()


def test_ask_text_help_blurb(make_console: MakeConsole) -> None:
    console, out = make_console("?\nLathe\n")
    value = prompts.ask_text(console, "name", help_key="project_name")
    assert value == "Lathe"
    assert "project file slug" in out.getvalue()


def test_ask_choice_validates(make_console: MakeConsole) -> None:
    console, out = make_console("oval\nsingle\n")
    value = prompts.ask_choice(console, "shape", ["single", "machine"])
    assert value == "single"
    assert "pick one of: single, machine" in out.getvalue()


def test_ask_choice_default(make_console: MakeConsole) -> None:
    console, _ = make_console("\n")
    value = prompts.ask_choice(console, "shape", ["single", "machine"], default="single")
    assert value == "single"


def test_ask_yes_no_accepts_y(make_console: MakeConsole) -> None:
    console, _ = make_console("y\n")
    assert prompts.ask_yes_no(console, "go?") is True


def test_ask_yes_no_default_false(make_console: MakeConsole) -> None:
    console, _ = make_console("\n")
    assert prompts.ask_yes_no(console, "go?", default=False) is False


def test_ask_int_minimum_enforced(make_console: MakeConsole) -> None:
    console, out = make_console("0\n3\n")
    value = prompts.ask_int(console, "qty", minimum=1, field_label="Quantity", help_key="quantity")
    assert value == 3
    assert "Quantity must be >= 1" in out.getvalue()


def test_ask_int_default(make_console: MakeConsole) -> None:
    console, _ = make_console("\n")
    value = prompts.ask_int(console, "qty", minimum=1, default=1)
    assert value == 1


def test_ask_decimal_returns_decimal(
    make_console: MakeConsole,
) -> None:
    console, _ = make_console("3.14\n")
    value = prompts.ask_decimal(console, "len", minimum=Decimal("0"))
    assert value == Decimal("3.14")


def test_ask_decimal_help_then_value(
    make_console: MakeConsole,
) -> None:
    console, out = make_console("?\n12.5\n")
    value = prompts.ask_decimal(
        console,
        "vol",
        minimum=Decimal("0"),
        help_key="volume",
        field_label="Volume",
    )
    assert value == Decimal("12.5")
    assert "Three ways to give a component" in out.getvalue()


def test_ask_decimal_zero_rejected(
    make_console: MakeConsole,
) -> None:
    console, out = make_console("0\n5\n")
    value = prompts.ask_decimal(
        console,
        "len",
        minimum=Decimal("0"),
        field_label="Length",
        help_key="volume",
    )
    assert value == Decimal("5")
    assert "Length must be > 0. (mixsheet help volume)" in out.getvalue()


def test_ask_decimal_non_numeric_rejected(
    make_console: MakeConsole,
) -> None:
    console, out = make_console("abc\n3\n")
    value = prompts.ask_decimal(console, "x", field_label="X", help_key="volume")
    assert value == Decimal("3")
    assert "X must be a number" in out.getvalue()


def test_ask_indexed_choice_picks_by_number(
    make_console: MakeConsole,
) -> None:
    console, _ = make_console("2\n")
    value = prompts.ask_indexed_choice(
        console,
        "pick",
        [("a", "Alpha"), ("b", "Beta"), ("c", "Gamma")],
    )
    assert value == "b"


def test_ask_indexed_choice_help_then_pick(
    make_console: MakeConsole,
) -> None:
    console, out = make_console("?\n1\n")
    value = prompts.ask_indexed_choice(
        console,
        "pick",
        [("a", "Alpha"), ("b", "Beta")],
        help_key="strategies",
    )
    assert value == "a"
    assert "Three picking strategies" in out.getvalue()
