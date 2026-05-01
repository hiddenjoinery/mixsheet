"""Rich-driven prompt helpers and ``?``-help dispatcher.

Every prompt accepts ``?`` as input and re-asks after printing the
prompt-specific blurb. Numeric inputs parse via :class:`Decimal`; choice
prompts validate against an explicit set. Validation errors loop the
prompt without losing wizard state.

The blurbs are short, in-flow, and end with a ``See: mixsheet help
<topic>`` pointer. The topic-help system itself ships in a follow-up
proposal; the pointer remains stable so help resolution can be wired
in later without touching the prompt sites.
"""

from __future__ import annotations

from decimal import Decimal, InvalidOperation
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from rich.console import Console

PROMPT_PROJECT_NAME = "project_name"
PROMPT_PROJECT_SHAPE = "project_shape"
PROMPT_COMPONENT_NAME = "component_name"
PROMPT_VOLUME_MODE = "volume_mode"
PROMPT_VOLUME_DIMENSIONS = "volume"
PROMPT_VOLUME_AREA = "volume"
PROMPT_VOLUME_DIRECT = "volume"
PROMPT_QUANTITY = "quantity"
PROMPT_BELOW_MIN = "volume"
PROMPT_PRESET = "preset"
PROMPT_ADD_ANOTHER = "add_another"
PROMPT_OVERAGE = "overage"
PROMPT_COMPARE = "strategies"
PROMPT_STRATEGY = "strategies"
PROMPT_RESUME_MENU = "resume"
PROMPT_UNKNOWN_PRESET = "preset"
PROMPT_UNPURCHASABLE = "purchase"

HELP_BLURBS: dict[str, str] = {
    "project_name": (
        "Project name is the human label printed on every artifact and used to\n"
        "build the project file slug.\n\n"
        "  Lathe bed riser   → ./projects/lathe-bed-riser.yaml\n"
        "  Router gantry     → ./projects/router-gantry/project.yaml\n\n"
        "See: mixsheet help projects"
    ),
    "project_shape": (
        "Shape decides the on-disk layout.\n\n"
        "  single   — one component, three sibling files\n"
        "  machine  — many components, one folder per project\n\n"
        "Both shapes use the same YAML schema; only the layout differs.\n\n"
        "See: mixsheet help projects"
    ),
    "component_name": (
        "Component name is the label on the mix-sheet tab and in the\n"
        "aggregated breakdown. Free text — pick what you'll recognise on the\n"
        "workbench.\n\n"
        "See: mixsheet help projects"
    ),
    "volume": (
        "Three ways to give a component its volume:\n\n"
        "  dimensions    — length x width x height in mm\n"
        "  area_height   — 2D area in mm² extruded by height in mm\n"
        "  direct        — litres straight up\n\n"
        "All inputs must be > 0. Volumes below 0.01 L trigger a confirmation;\n"
        "the wizard does not target sub-cl pours.\n\n"
        "See: mixsheet help volume"
    ),
    "quantity": (
        "Quantity is how many copies of this component are poured. Integer\n"
        "≥ 1. Net volume is volume x quantity.\n\n"
        "See: mixsheet help projects"
    ),
    "preset": (
        "Mix preset decides density and per-material proportions. The chosen\n"
        "preset's version is pinned at save time so re-opening the project\n"
        "warns when the catalog moves on.\n\n"
        "See: mixsheet help presets"
    ),
    "add_another": (
        "Add another component to the same machine project, or finish the\n"
        "component loop and move on to overage + strategy.\n\n"
        "See: mixsheet help projects"
    ),
    "overage": (
        "Project overage covers mixing losses, supplier rounding, dropped\n"
        "bags and re-pour margin in one number. Default 10%.\n\n"
        "  0%   — precise calculation, you accept zero margin\n"
        "  5%   — clean pour, well-defined geometry\n"
        " 10%   — typical workshop use (default)\n"
        " 20%+  — restocking anyway, or a risky pour\n\n"
        "See: mixsheet help overage"
    ),
    "strategies": (
        "Three picking strategies for the optimiser:\n\n"
        "  cheapest        — lowest total cost (waste as tiebreaker)\n"
        "  bulk_value      — lowest €/kg (cost as tiebreaker)\n"
        "  minimal_waste   — least leftover (cost as tiebreaker)\n\n"
        "Comparison runs all three so tradeoffs are visible.\n\n"
        "See: mixsheet help strategies"
    ),
    "resume": (
        'Pick what to do with this loaded project. "Continue" jumps to the\n'
        'next prompt the project file does not yet answer. "Quit" leaves the\n'
        "file untouched.\n\n"
        "See: mixsheet help projects"
    ),
    "purchase": (
        "When a material has no purchasable package the optimiser cannot\n"
        "produce a line item. Either skip it for this run, add it to the\n"
        "project's excluded materials so it is remembered, or quit.\n\n"
        "See: mixsheet help projects"
    ),
}


def _help_pointer(help_key: str | None) -> str:
    """Return the ``(mixsheet help <topic>)`` see-also string."""
    if help_key is None:
        return ""
    topic = help_key.split("_")[0]
    return f" (mixsheet help {topic})"


def _read(console: Console, prompt: str, default: str | None) -> str:
    suffix = f" [{default}]" if default is not None else ""
    raw = console.input(f"{prompt}{suffix}: ").strip()
    if raw == "" and default is not None:
        return default
    return raw


def _maybe_help(console: Console, raw: str, help_key: str | None) -> bool:
    if raw == "?" and help_key is not None:
        blurb = HELP_BLURBS.get(help_key)
        if blurb is not None:
            console.print(blurb)
        return True
    return False


def ask_text(
    console: Console,
    prompt: str,
    *,
    help_key: str | None = None,
    default: str | None = None,
    allow_empty: bool = False,
) -> str:
    """Read a non-empty trimmed text answer with ``?``-help and re-prompt loop."""
    while True:
        raw = _read(console, prompt, default)
        if _maybe_help(console, raw, help_key):
            continue
        if not raw and not allow_empty:
            console.print("  ! must not be empty.")
            continue
        return raw


def ask_choice(
    console: Console,
    prompt: str,
    choices: list[str],
    *,
    help_key: str | None = None,
    default: str | None = None,
) -> str:
    """Read one of ``choices`` (case-sensitive) with ``?``-help."""
    label = f"{prompt} [{'/'.join(choices)}]"
    while True:
        raw = _read(console, label, default)
        if _maybe_help(console, raw, help_key):
            continue
        if raw not in choices:
            console.print(f"  ! pick one of: {', '.join(choices)}.")
            continue
        return raw


def ask_yes_no(
    console: Console,
    prompt: str,
    *,
    help_key: str | None = None,
    default: bool = False,
) -> bool:
    """Read ``y`` / ``n`` (case-insensitive) with ``?``-help."""
    suffix = "Y/n" if default else "y/N"
    while True:
        raw = _read(console, f"{prompt} [{suffix}]", "y" if default else "n").lower()
        if _maybe_help(console, raw, help_key):
            continue
        if raw in {"y", "yes"}:
            return True
        if raw in {"n", "no"}:
            return False
        console.print("  ! please answer y or n.")


def ask_int(  # noqa: PLR0913
    console: Console,
    prompt: str,
    *,
    minimum: int,
    help_key: str | None = None,
    default: int | None = None,
    field_label: str | None = None,
) -> int:
    """Read an integer ≥ ``minimum`` with ``?``-help and labelled errors."""
    label = field_label or prompt
    while True:
        raw = _read(console, prompt, None if default is None else str(default))
        if _maybe_help(console, raw, help_key):
            continue
        try:
            value = int(raw)
        except ValueError:
            console.print(f"  ! {label} must be an integer.{_help_pointer(help_key)}")
            continue
        if value < minimum:
            console.print(
                f"  ! {label} must be >= {minimum}.{_help_pointer(help_key)}",
            )
            continue
        return value


def ask_decimal(  # noqa: PLR0913
    console: Console,
    prompt: str,
    *,
    minimum: Decimal | None = None,
    help_key: str | None = None,
    default: str | None = None,
    field_label: str | None = None,
) -> Decimal:
    """Read a positive ``Decimal`` with ``?``-help and labelled errors."""
    label = field_label or prompt
    while True:
        raw = _read(console, prompt, default)
        if _maybe_help(console, raw, help_key):
            continue
        try:
            value = Decimal(raw)
        except InvalidOperation, ValueError:
            console.print(f"  ! {label} must be a number.{_help_pointer(help_key)}")
            continue
        if minimum is not None and value <= minimum:
            console.print(
                f"  ! {label} must be > {minimum}.{_help_pointer(help_key)}",
            )
            continue
        return value


def ask_indexed_choice(
    console: Console,
    prompt: str,
    options: list[tuple[str, str]],
    *,
    help_key: str | None = None,
) -> str:
    """Print numbered ``options`` and return the chosen item's id.

    ``options`` is a list of ``(id, label)`` tuples; the user picks by
    index (1-based). ``?`` prints the help blurb without consuming the
    pick.
    """
    while True:
        for index, (_, label) in enumerate(options, start=1):
            console.print(f"  {index}. {label}")
        raw = _read(console, prompt, None)
        if _maybe_help(console, raw, help_key):
            continue
        try:
            choice = int(raw)
        except ValueError:
            console.print(f"  ! pick a number between 1 and {len(options)}.")
            continue
        if not 1 <= choice <= len(options):
            console.print(f"  ! pick a number between 1 and {len(options)}.")
            continue
        return options[choice - 1][0]
