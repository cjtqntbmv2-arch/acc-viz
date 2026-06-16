from __future__ import annotations

"""Plotly histogram figure construction for per-plate band-RMS distributions."""

import numpy as np
import plotly.graph_objects as go

from src.ui import strings as S

HISTOGRAM_HEIGHT = 300
BAR_COLOR = "#4C78A8"
REF_LINE_COLOR = "rgba(255,255,0,0.9)"
_INTEGER_TICK_THRESHOLD = 10


def make_histogram(
    values: np.ndarray,
    *,
    bins: int,
    normalized: bool,
    ref_value: float | None = None,
    x_range: tuple[float, float] | None = None,
    show_stats: bool = False,
) -> go.Figure:
    """Build a Plotly histogram of band-RMS values for a single plate.

    Non-finite entries in ``values`` are filtered out before binning. The
    effective bin count is capped at the number of finite values so that
    sparse measurements do not produce many empty bins.

    Args:
        values: 1D array of band-RMS values (typically ``grid.ravel()``).
            May contain NaN entries for missing hole positions.
        bins: User-selected upper bound on the bin count.
        normalized: When ``True`` the x-axis is labelled as a normalized
            ratio; otherwise as absolute g RMS.
        ref_value: Optional reference value drawn as a dashed yellow
            vertical line for visual comparison with the heatmap reference.
        x_range: Optional ``(xmin, xmax)`` to align the x-axis across
            plates (mirrors the heatmap shared-scale behaviour).

    Returns:
        A :class:`plotly.graph_objects.Figure` ready to be rendered.
        For empty inputs, the figure contains an annotation instead of a
        bar trace.
    """
    finite = values[np.isfinite(values)]

    if finite.size == 0:
        fig = go.Figure()
        fig.add_annotation(
            text=S.HISTOGRAM_EMPTY,
            xref="paper", yref="paper",
            x=0.5, y=0.5, showarrow=False,
        )
        fig.update_layout(
            height=HISTOGRAM_HEIGHT,
            margin=dict(l=40, r=20, t=20, b=40),
            xaxis=dict(visible=False),
            yaxis=dict(visible=False),
        )
        return fig

    eff_bins = min(bins, max(1, int(finite.size)))
    counts, edges = np.histogram(finite, bins=eff_bins, range=x_range)

    label = S.COLORBAR_NORMALIZED if normalized else S.COLORBAR_ABSOLUTE

    fig = go.Figure(
        go.Bar(
            x=edges[:-1],
            y=counts.astype(int),
            width=np.diff(edges),
            marker_color=BAR_COLOR,
            customdata=np.stack([edges[:-1], edges[1:]], axis=-1),
            hovertemplate=(
                f"[%{{customdata[0]:.4f}}, %{{customdata[1]:.4f}})<br>"
                "Anzahl=%{y}<extra></extra>"
            ),
        )
    )

    if ref_value is not None:
        fig.add_vline(
            x=ref_value,
            line=dict(color=REF_LINE_COLOR, dash="dash", width=2),
        )

    if show_stats and finite.size >= 2:
        mean = float(np.mean(finite))
        median = float(np.median(finite))
        std = float(np.std(finite))
        fig.add_vline(
            x=mean, line=dict(color="#D62728", width=2),
            annotation_text=S.HISTOGRAM_STAT_MEAN.format(value=mean),
        )
        fig.add_vline(
            x=median, line=dict(color="#2CA02C", dash="dash", width=2),
            annotation_text=S.HISTOGRAM_STAT_MEDIAN.format(value=median),
        )
        fig.add_vline(x=mean - std, line=dict(color="#9467BD", dash="dot", width=1.5))
        fig.add_vline(
            x=mean + std, line=dict(color="#9467BD", dash="dot", width=1.5),
            annotation_text=S.HISTOGRAM_STAT_SIGMA.format(value=std),
        )

    fig.update_layout(
        xaxis_title=S.HISTOGRAM_X_LABEL_TMPL.format(label=label),
        yaxis_title=S.HISTOGRAM_Y_LABEL,
        height=HISTOGRAM_HEIGHT,
        margin=dict(l=40, r=20, t=20, b=40),
        bargap=0.05,
        showlegend=False,
    )

    # counts is non-empty here — the empty-input branch returns earlier.
    if int(counts.max()) <= _INTEGER_TICK_THRESHOLD:
        fig.update_yaxes(dtick=1)

    if x_range is not None:
        fig.update_xaxes(range=list(x_range))

    return fig
