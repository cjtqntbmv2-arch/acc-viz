from __future__ import annotations

"""Streamlit CSV-export download button.

The pure ``build_export_dataframe`` now lives in the frontend-agnostic
:mod:`src.core.export` and is re-exported here for backward compatibility.
"""

import streamlit as st

from src.core.export import PlateMapping, build_export_dataframe, export_csv_bytes
from src.core.settings import Axis
from src.ui import strings as S

__all__ = ["build_export_dataframe", "render_csv_export"]


def render_csv_export(
    plates: PlateMapping,
    *,
    f_min: int,
    f_max: int,
    axis: Axis,
) -> None:
    """Render a sidebar download button that serves the aggregated CSV export.

    The CSV is encoded as UTF-8 with BOM and uses ``;`` as the field separator
    for Excel compatibility in German locales.

    Args:
        plates: Mapping from plate name to ``(hole_data, ref_df)`` tuples, as
            consumed by :func:`build_export_dataframe`.
        f_min: Lower band edge in Hz.
        f_max: Upper band edge in Hz.
        axis: Axis whose PSD column to integrate. Accepts ``"X"``, ``"Y"``,
            ``"Z"``, or ``"RSS"`` (Root Sum of Squares over all three axes).
    """
    st.sidebar.download_button(
        label=S.CSV_EXPORT,
        data=export_csv_bytes(plates, f_min=f_min, f_max=f_max, axis=axis),
        file_name="beschleunigung_export.csv",
        mime="text/csv",
        help=S.HELP_CSV_EXPORT,
    )
