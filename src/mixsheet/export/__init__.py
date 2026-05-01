"""Excel export surface for The Mix Sheet.

Two pure write functions consume frozen domain views plus a
:class:`ProjectHeader` and produce ``.xlsx`` workbooks. ``xlsxwriter``
is an optional extra (``uv add mixsheet[export]``); both writers import
it lazily and raise :class:`MissingExcelExtraError` when the extra is
absent. The writers never reach back into the catalog or the
optimizer; the caller hands views in.
"""

from __future__ import annotations

from mixsheet.export.excel import (
    MissingExcelExtraError,
    ProjectHeader,
    write_mixsheet_workbook,
    write_purchase_workbook,
)

__all__ = [
    "MissingExcelExtraError",
    "ProjectHeader",
    "write_mixsheet_workbook",
    "write_purchase_workbook",
]
