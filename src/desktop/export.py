from __future__ import annotations

"""CSV export for the desktop app — native save dialog + file write.

Reuses the frontend-agnostic :func:`src.core.export.export_csv_bytes`, so the
exported file is byte-for-byte identical to the Streamlit download.
"""

from pathlib import Path

from src.core.export import PlateMapping, export_csv_bytes
from src.core.settings import Axis
from src.ui import strings as S

_DEFAULT_FILENAME = "beschleunigung_export.csv"


def save_export(
    plates: PlateMapping,
    path: str,
    *,
    f_min: int,
    f_max: int,
    axis: Axis,
) -> None:
    """Write the aggregated export CSV to ``path``."""
    data = export_csv_bytes(plates, f_min=f_min, f_max=f_max, axis=axis)
    Path(path).write_bytes(data)


def prompt_export(
    parent,
    plates: PlateMapping,
    *,
    f_min: int,
    f_max: int,
    axis: Axis,
) -> str | None:
    """Show a native save dialog and write the export there.

    Args:
        parent: Parent widget for the dialog (may be ``None``).
        plates: Mapping from plate name to ``(hole_data, ref_df)`` tuples.
        f_min: Lower band edge in Hz.
        f_max: Upper band edge in Hz.
        axis: Axis whose PSD column to integrate.

    Returns:
        The chosen path when the file was written, or ``None`` if cancelled.
    """
    from PySide6.QtWidgets import QFileDialog

    path, _ = QFileDialog.getSaveFileName(
        parent, S.CSV_EXPORT, _DEFAULT_FILENAME, "CSV (*.csv)"
    )
    if not path:
        return None
    save_export(plates, path, f_min=f_min, f_max=f_max, axis=axis)
    return path
