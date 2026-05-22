from __future__ import annotations

import numpy as np
import pytest

from src.desktop.plots.heatmap_canvas import (
    HeatmapCanvas,
    colorscale_to_cmap,
    nearest_cell,
)


# --- pure helpers ----------------------------------------------------------

@pytest.mark.parametrize("name,expected", [
    ("Viridis", "viridis"),
    ("Plasma", "plasma"),
    ("Hot", "hot"),
    ("RdBu", "RdBu"),
    ("Cividis", "cividis"),
    ("Turbo", "turbo"),
    ("Inferno", "inferno"),
])
def test_colorscale_to_cmap_known(name, expected):
    assert colorscale_to_cmap(name) == expected


def test_colorscale_to_cmap_unknown_falls_back_to_viridis():
    assert colorscale_to_cmap("NopeNotReal") == "viridis"


def test_nearest_cell_rounds_to_integer_grid():
    # grid shape (nrows=2, ncols=2): x in 0..1, y in 0..1
    assert nearest_cell(0.1, 0.9, 2, 2) == (0, 1)
    assert nearest_cell(0.51, 0.49, 2, 2) == (1, 0)


def test_nearest_cell_out_of_bounds_returns_none():
    assert nearest_cell(-0.9, 0.0, 2, 2) is None
    assert nearest_cell(0.0, 5.0, 2, 2) is None


def test_nearest_cell_none_coords_returns_none():
    assert nearest_cell(None, None, 2, 2) is None


# --- canvas widget ---------------------------------------------------------

def test_heatmap_canvas_render_does_not_raise(qapp):
    canvas = HeatmapCanvas()
    grid = np.array([[1.0, 2.0], [3.0, 4.0]])
    canvas.render_grid(
        grid,
        plate_name="Platte 1",
        title="Platte 1",
        colorscale="Viridis",
        normalized=False,
        hole_positions=[(0, 0), (1, 1)],
        hole_values=[1.0, 4.0],
        ref_value=None,
        z_range=(1.0, 4.0),
    )


def test_heatmap_canvas_click_emits_holeclicked(qapp):
    canvas = HeatmapCanvas()
    grid = np.array([[1.0, 2.0], [3.0, 4.0]])
    canvas.render_grid(
        grid, plate_name="Platte 1", title="t", colorscale="Viridis",
        normalized=False, hole_positions=[(0, 0)], hole_values=[1.0],
        ref_value=None, z_range=None,
    )
    received = []
    canvas.holeClicked.connect(lambda name, x, y: received.append((name, x, y)))

    # Simulate a matplotlib click in data coordinates at cell (1, 0).
    class _Evt:
        inaxes = canvas.axes
        xdata = 1.0
        ydata = 0.0
        button = 1

    canvas._on_click(_Evt())
    assert received == [("Platte 1", 1, 0)]
