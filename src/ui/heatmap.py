from __future__ import annotations

"""Plotly heatmap figure construction for interpolated plate grids."""

import numpy as np
import plotly.graph_objects as go

from src.ui import strings as S

HEATMAP_HEIGHT = 600
HOLE_MARKER_SIZE = 8
REF_STAR_SIZE = 14


def make_heatmap(
    grid: np.ndarray,
    *,
    title: str,
    colorscale: str,
    normalized: bool,
    hole_positions: list[tuple[int, int]],
    hole_values: list[float],
    ref_value: float | None,
    z_range: tuple[float, float] | None,
) -> go.Figure:
    """Build a Plotly heatmap figure for the interpolated grid.

    Overlays white hole markers at the measured positions and — when provided
    — a yellow star at the geometric center representing the reference value.

    Args:
        grid: 2D array of interpolated values with shape ``(max_x + 1, max_y + 1)``.
        title: Figure title.
        colorscale: Plotly colorscale identifier (e.g. ``"Viridis"``).
        normalized: If true, label the colorbar as normalized; otherwise as
            absolute g RMS.
        hole_positions: 0-indexed ``(x, y)`` positions for measured holes.
        hole_values: Displayed values for the hole markers, aligned with
            ``hole_positions``.
        ref_value: Optional reference value rendered at the grid center.
        z_range: Optional ``(zmin, zmax)`` color range; when ``None`` Plotly
            auto-ranges.

    Returns:
        A :class:`plotly.graph_objects.Figure` ready to be rendered.
    """
    nrows, ncols = grid.shape
    label = S.COLORBAR_NORMALIZED if normalized else S.COLORBAR_ABSOLUTE

    if not np.isfinite(grid).any():
        fig = go.Figure()
        fig.add_annotation(
            text=S.HEATMAP_EMPTY,
            xref="paper", yref="paper", x=0.5, y=0.5, showarrow=False,
        )
        fig.update_layout(
            title=title,
            height=HEATMAP_HEIGHT,
            xaxis=dict(visible=False),
            yaxis=dict(visible=False),
        )
        return fig

    fig = go.Figure(
        go.Heatmap(
            z=grid.T,
            x=list(range(0, nrows)),
            y=list(range(0, ncols)),
            colorscale=colorscale,
            zmin=z_range[0] if z_range else None,
            zmax=z_range[1] if z_range else None,
            colorbar=dict(title=label),
            hoverongaps=False,
            hovertemplate=f"x=%{{x}}, y=%{{y}}<br>Interpoliert ({label})=%{{z:.4f}}<extra></extra>",
        )
    )
    fig.add_trace(go.Scatter(
        x=[x for (x, _) in hole_positions],
        y=[y for (_, y) in hole_positions],
        mode="markers",
        marker=dict(
            size=HOLE_MARKER_SIZE,
            color="rgba(255,255,255,0.4)",
            line=dict(color="rgba(0,0,0,0.7)", width=1.5),
        ),
        customdata=hole_values,
        hovertemplate=f"x=%{{x}}, y=%{{y}}<br>{label}=%{{customdata:.4f}}<extra></extra>",
        showlegend=False,
    ))
    if ref_value is not None:
        fig.add_trace(go.Scatter(
            x=[(nrows - 1) / 2],
            y=[(ncols - 1) / 2],
            mode="markers",
            marker=dict(
                size=REF_STAR_SIZE,
                symbol="star",
                color="rgba(255,255,0,0.9)",
                line=dict(color="black", width=1.5),
            ),
            customdata=[ref_value],
            hovertemplate=f"Referenz (Mitte)<br>{label}=%{{customdata:.4f}}<extra></extra>",
            showlegend=False,
        ))

    fig.update_layout(
        title=title,
        xaxis_title=S.HEATMAP_X_LABEL,
        yaxis_title=S.HEATMAP_Y_LABEL,
        height=HEATMAP_HEIGHT,
    )
    fig.update_yaxes(
        scaleanchor="x",
        scaleratio=1,
        constrain="domain",
        autorange="reversed",
        dtick=1,
    )
    fig.update_xaxes(constrain="domain", dtick=1)
    return fig
