from __future__ import annotations

import numpy as np
import plotly.graph_objects as go

from src.ui.heatmap import make_heatmap


def _make(grid):
    return make_heatmap(
        grid,
        title="P1",
        colorscale="Viridis",
        normalized=False,
        hole_positions=[],
        hole_values=[],
        ref_value=None,
        z_range=None,
    )


def test_make_heatmap_all_nan_shows_empty_annotation():
    grid = np.full((3, 3), np.nan)
    fig = _make(grid)
    texts = [a.text for a in fig.layout.annotations]
    assert any("Frequenzband" in t for t in texts)


def test_make_heatmap_with_data_has_heatmap_trace_and_no_empty_annotation():
    grid = np.array([[1.0, 2.0], [3.0, 4.0]])
    fig = _make(grid)
    assert any(isinstance(t, go.Heatmap) for t in fig.data)
    texts = [a.text for a in fig.layout.annotations]
    assert not any("Frequenzband" in t for t in texts)
