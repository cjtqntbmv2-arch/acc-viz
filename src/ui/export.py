from __future__ import annotations

"""CSV export of aggregated per-hole band-RMS results for all plates."""

import math
from collections.abc import Mapping
from typing import Literal

import pandas as pd
import streamlit as st

from src.analysis.rms import compute_band_rms
from src.ui import strings as S


def build_export_dataframe(
    plates: Mapping[str, tuple[Mapping[tuple[int, int], pd.DataFrame], pd.DataFrame | None]],
    *,
    f_min: int,
    f_max: int,
    axis: Literal["X", "Y", "Z", "RSS"],
) -> pd.DataFrame:
    """Assemble a tidy DataFrame with one row per ``(plate, x, y)``.

    For each hole, computes the absolute band-RMS and — if a valid reference
    DataFrame is available — the normalized band-RMS (absolute divided by the
    reference RMS).

    Args:
        plates: Mapping from plate name to a ``(hole_data, ref_df)`` tuple,
            where ``hole_data`` maps ``(x, y)`` coordinates to measurement
            DataFrames and ``ref_df`` is the optional reference DataFrame.
        f_min: Lower band edge in Hz.
        f_max: Upper band edge in Hz.
        axis: Axis whose PSD column to integrate. Accepts ``"X"``, ``"Y"``,
            ``"Z"``, or ``"RSS"`` (Root Sum of Squares over all three axes).

    Returns:
        A DataFrame with columns ``plate``, ``x``, ``y``, ``axis``,
        ``f_min_hz``, ``f_max_hz``, ``band_rms_abs`` and
        ``band_rms_normalized``. ``band_rms_normalized`` is ``NaN`` where no
        usable reference value is available.
    """
    rows = []
    for name, (hole_data, ref_df) in plates.items():
        ref_rms = (
            compute_band_rms(ref_df, f_min, f_max, axis) if ref_df is not None else None
        )
        for (x, y), df in sorted(hole_data.items()):
            rms_abs = compute_band_rms(df, f_min, f_max, axis)
            norm: float = math.nan
            if (
                ref_rms is not None
                and not math.isnan(ref_rms)
                and ref_rms > 0
                and not math.isnan(rms_abs)
            ):
                norm = rms_abs / ref_rms
            rows.append({
                "plate": name,
                "x": x,
                "y": y,
                "axis": axis,
                "f_min_hz": f_min,
                "f_max_hz": f_max,
                "band_rms_abs": rms_abs,
                "band_rms_normalized": norm,
            })
    return pd.DataFrame(rows)


def render_csv_export(
    plates: Mapping[str, tuple[Mapping[tuple[int, int], pd.DataFrame], pd.DataFrame | None]],
    *,
    f_min: int,
    f_max: int,
    axis: Literal["X", "Y", "Z", "RSS"],
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
    df = build_export_dataframe(plates, f_min=f_min, f_max=f_max, axis=axis)
    csv_bytes = df.to_csv(index=False, sep=";").encode("utf-8-sig")
    st.sidebar.download_button(
        label=S.CSV_EXPORT,
        data=csv_bytes,
        file_name="beschleunigung_export.csv",
        mime="text/csv",
        help=S.HELP_CSV_EXPORT,
    )
