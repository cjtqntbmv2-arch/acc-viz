from __future__ import annotations

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
    nrows, ncols = grid.shape
    label = S.COLORBAR_NORMALIZED if normalized else S.COLORBAR_ABSOLUTE

    fig = go.Figure(
        go.Heatmap(
            z=grid.T,
            x=list(range(1, nrows + 1)),
            y=list(range(1, ncols + 1)),
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
            x=[(nrows + 1) / 2],
            y=[(ncols + 1) / 2],
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
    fig.update_yaxes(scaleanchor="x", scaleratio=1, constrain="domain", autorange="reversed")
    fig.update_xaxes(constrain="domain")
    return fig
