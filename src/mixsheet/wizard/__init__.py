"""Interactive Typer + Rich wizard for The Mix Sheet.

Composes the existing pure domain capabilities (project I/O, calculator,
aggregator, optimizer, renderers) and the optional Excel writer into the
two top-level CLI commands ``mixsheet new`` and ``mixsheet open``.

The wizard owns no business logic. It prompts, validates, persists each
answer through :func:`mixsheet.domain.save_project`, and dispatches to
domain functions when the user advances.
"""

from __future__ import annotations

from mixsheet.wizard.new import run_new
from mixsheet.wizard.open import run_open

__all__ = ["run_new", "run_open"]
