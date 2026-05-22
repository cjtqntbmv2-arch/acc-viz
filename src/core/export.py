from __future__ import annotations

"""Frontend-agnostic CSV export of aggregated per-hole band-RMS results.

Extracted from the original Streamlit ``src.ui.export`` so the same export logic
can drive any frontend (Streamlit download button, Qt save dialog). No Streamlit
import here on purpose.
"""

import math
from collections.abc import Mapping

import pandas as pd

from src.analysis.rms import compute_band_rms
from src.core.settings import Axis

PlateMapping = Mapping[
    str, tuple[Mapping[tuple[int, int], pd.DataFrame], pd.DataFrame | None]
]


def build_export_dataframe(
    plates: PlateMapping,
    *,
    f_min: int,
    f_max: int,
    axis: Axis,
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


def export_csv_bytes(
    plates: PlateMapping,
    *,
    f_min: int,
    f_max: int,
    axis: Axis,
) -> bytes:
    """Build the aggregated export CSV as UTF-8-with-BOM, ``;``-separated bytes.

    Uses ``;`` as the field separator and a UTF-8 BOM for Excel compatibility
    in German locales (matching the original Streamlit download).
    """
    df = build_export_dataframe(plates, f_min=f_min, f_max=f_max, axis=axis)
    return df.to_csv(index=False, sep=";").encode("utf-8-sig")
