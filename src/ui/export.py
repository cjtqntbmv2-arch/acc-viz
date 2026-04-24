from __future__ import annotations

import math
import pandas as pd
import streamlit as st

from src.analysis.rms import compute_band_rms
from src.ui import strings as S


def build_export_dataframe(
    plates: dict[str, tuple[dict[tuple[int, int], pd.DataFrame], pd.DataFrame | None]],
    *,
    f_min: int,
    f_max: int,
    axis: str,
) -> pd.DataFrame:
    rows = []
    for name, (hole_data, ref_df) in plates.items():
        ref_rms = (
            compute_band_rms(ref_df, f_min, f_max, axis) if ref_df is not None else None
        )
        for (x, y), df in sorted(hole_data.items()):
            rms_abs = compute_band_rms(df, f_min, f_max, axis)
            norm = ""
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


def render_csv_export(plates, *, f_min: int, f_max: int, axis: str) -> None:
    df = build_export_dataframe(plates, f_min=f_min, f_max=f_max, axis=axis)
    csv_bytes = df.to_csv(index=False).encode("utf-8")
    st.sidebar.download_button(
        label=S.CSV_EXPORT,
        data=csv_bytes,
        file_name="beschleunigung_export.csv",
        mime="text/csv",
    )
