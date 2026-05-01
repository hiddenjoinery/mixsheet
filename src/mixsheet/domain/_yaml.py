"""YAML helpers that preserve ``Decimal`` precision.

Default ``yaml.safe_load`` parses ``1.91`` as a Python ``float``, which
loses precision and is rejected by Pydantic's strict ``Decimal`` mode.
:func:`safe_load_decimal` substitutes a constructor that returns
:class:`decimal.Decimal` for every float node, built from the original
string representation in the YAML file.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Any

import yaml


class _DecimalSafeLoader(yaml.SafeLoader):
    """A ``SafeLoader`` subclass that yields ``Decimal`` for YAML floats."""


def _decimal_constructor(_loader: yaml.SafeLoader, node: yaml.ScalarNode) -> Decimal:
    return Decimal(node.value)


_DecimalSafeLoader.add_constructor("tag:yaml.org,2002:float", _decimal_constructor)


def safe_load_decimal(text: str) -> Any:
    """Parse YAML with floats promoted to :class:`Decimal`.

    Behaves like :func:`yaml.safe_load` for every other tag, including
    refusing unsafe Python-object tags.
    """
    return yaml.load(text, Loader=_DecimalSafeLoader)  # noqa: S506 - safe loader subclass
