from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from src.ui import strings as S

SPECTRUM_HEIGHT = 350


def render_spectrum(
    *,
    plate_name: str,
    x_hole: int,
    y_hole: int,
    axis: str,
    hole_df: pd.DataFrame,
    ref_df: pd.DataFrame | None,
    f_min: int,
    f_max: int,
) -> None:
    col_psd = f"PSD_{axis}_g2Hz"
    st.subheader(S.SPECTRUM_TITLE.format(name=plate_name, x=x_hole, y=y_hole, axis=axis))

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=hole_df["Frequenz_Hz"],
        y=hole_df[col_psd],
        name=S.SPECTRUM_TRACE_HOLE.format(x=x_hole, y=y_hole),
        line=dict(width=1.5),
    ))
    if ref_df is not None:
        fig.add_trace(go.Scatter(
            x=ref_df["Frequenz_Hz"],
            y=ref_df[col_psd],
            name=S.SPECTRUM_TRACE_REF,
            line=dict(color="grey", width=1, dash="dash"),
        ))
    fig.add_vrect(x0=f_min, x1=f_max, fillcolor="yellow", opacity=0.1, line_width=0)
    fig.update_layout(
        xaxis_title=S.SPECTRUM_X_LABEL,
        yaxis_title=S.SPECTRUM_Y_LABEL_TMPL.format(axis=axis),
        yaxis_type="log",
        height=SPECTRUM_HEIGHT,
        legend=dict(orientation="h"),
    )
    st.plotly_chart(fig, use_container_width=True)
