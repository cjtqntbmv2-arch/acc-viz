from __future__ import annotations

"""Per-hole PSD spectrum plot with an optional reference overlay."""

from typing import Literal

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from src.analysis.rms import rss_series
from src.ui import strings as S

SPECTRUM_HEIGHT = 350

Axis = Literal["X", "Y", "Z", "RSS"]
_SINGLE_AXES: tuple[Literal["X", "Y", "Z"], ...] = ("X", "Y", "Z")


def _add_single_axis_traces(
    fig: go.Figure,
    hole_df: pd.DataFrame,
    ref_df: pd.DataFrame | None,
    axis: Literal["X", "Y", "Z"],
    x_hole: int,
    y_hole: int,
) -> None:
    """Add traces for a single-axis PSD plot (hole + optional reference).

    Args:
        fig: Target Plotly figure.
        hole_df: Measurement DataFrame for the selected hole.
        ref_df: Optional reference measurement DataFrame.
        axis: Single axis whose PSD column is plotted.
        x_hole: 1-indexed x coordinate of the hole (for the legend label).
        y_hole: 1-indexed y coordinate of the hole (for the legend label).
    """
    col_psd = f"PSD_{axis}_g2Hz"
    y_series = hole_df[col_psd].clip(lower=1e-30)
    hole_trace_name = S.SPECTRUM_TRACE_HOLE.format(x=x_hole, y=y_hole)

    fig.add_trace(
        go.Scatter(
            x=hole_df["Frequenz_Hz"],
            y=y_series,
            name=hole_trace_name,
            line=dict(width=1.5),
        )
    )
    if ref_df is not None:
        y_ref = ref_df[col_psd].clip(lower=1e-30)
        fig.add_trace(
            go.Scatter(
                x=ref_df["Frequenz_Hz"],
                y=y_ref,
                name=S.SPECTRUM_TRACE_REF,
                line=dict(color="grey", width=1, dash="dash"),
            )
        )


def _add_rss_traces(
    fig: go.Figure,
    hole_df: pd.DataFrame,
    ref_df: pd.DataFrame | None,
) -> None:
    """Add traces for the RSS view: three thin per-axis lines and the bold sum.

    The three individual axes (X, Y, Z) are rendered as thin, slightly
    translucent lines so the bold, neutral-coloured sum trace stays visually
    dominant. If a reference is supplied, only the summed reference is drawn
    (as a dashed grey line) to avoid cluttering the chart.

    Args:
        fig: Target Plotly figure.
        hole_df: Measurement DataFrame for the selected hole.
        ref_df: Optional reference measurement DataFrame.
    """
    for a in _SINGLE_AXES:
        y_axis = hole_df[f"PSD_{a}_g2Hz"].clip(lower=1e-30)
        fig.add_trace(
            go.Scatter(
                x=hole_df["Frequenz_Hz"],
                y=y_axis,
                name=S.SPECTRUM_TRACE_AXIS_TMPL.format(axis=a),
                line=dict(width=1),
                opacity=0.7,
            )
        )

    sum_series = rss_series(hole_df).clip(lower=1e-30)
    fig.add_trace(
        go.Scatter(
            x=hole_df["Frequenz_Hz"],
            y=sum_series,
            name=S.SPECTRUM_TRACE_SUM,
            line=dict(width=2.5, color="black"),
        )
    )

    if ref_df is not None:
        ref_sum = rss_series(ref_df).clip(lower=1e-30)
        fig.add_trace(
            go.Scatter(
                x=ref_df["Frequenz_Hz"],
                y=ref_sum,
                name=S.SPECTRUM_TRACE_REF,
                line=dict(color="grey", width=1.2, dash="dash"),
            )
        )


def render_spectrum(
    *,
    plate_name: str,
    x_hole: int,
    y_hole: int,
    axis: Axis,
    hole_df: pd.DataFrame,
    ref_df: pd.DataFrame | None,
    f_min: int,
    f_max: int,
) -> None:
    """Render a Streamlit spectrum chart for one hole with the selected axis.

    The selected ``[f_min, f_max]`` band is highlighted with a translucent
    yellow rectangle. Y-values are clipped to ``1e-30`` before plotting so the
    logarithmic y-axis does not choke on zeros.

    For single-axis modes (``"X"``, ``"Y"``, ``"Z"``), the hole's PSD is drawn
    as a solid line; when ``ref_df`` is available, the reference spectrum is
    overlaid as a dashed grey line.

    For ``axis='RSS'``, the three individual axes (X, Y, Z) are rendered as
    thin overlayed lines and the summed PSD (``PSD_X + PSD_Y + PSD_Z``) is
    rendered on top as a bold line. The reference, if available, is shown as
    a single dashed summed reference line to keep the plot readable.

    Args:
        plate_name: Plate label used in the chart title.
        x_hole: 1-indexed x coordinate of the hole.
        y_hole: 1-indexed y coordinate of the hole.
        axis: Axis whose PSD is plotted; ``"RSS"`` triggers the summed view.
        hole_df: Measurement DataFrame for the selected hole.
        ref_df: Optional reference measurement DataFrame.
        f_min: Lower edge of the highlighted frequency band in Hz.
        f_max: Upper edge of the highlighted frequency band in Hz.
    """
    st.subheader(
        S.SPECTRUM_TITLE.format(name=plate_name, x=x_hole, y=y_hole, axis=axis)
    )

    fig = go.Figure()
    if axis == "RSS":
        _add_rss_traces(fig, hole_df, ref_df)
        y_label = S.SPECTRUM_Y_LABEL_RSS
    else:
        _add_single_axis_traces(fig, hole_df, ref_df, axis, x_hole, y_hole)
        y_label = S.SPECTRUM_Y_LABEL_TMPL.format(axis=axis)

    fig.add_vrect(x0=f_min, x1=f_max, fillcolor="yellow", opacity=0.1, line_width=0)
    fig.update_layout(
        xaxis_title=S.SPECTRUM_X_LABEL,
        yaxis_title=y_label,
        yaxis_type="log",
        height=SPECTRUM_HEIGHT,
        legend=dict(orientation="h"),
    )
    st.plotly_chart(fig, use_container_width=True)
