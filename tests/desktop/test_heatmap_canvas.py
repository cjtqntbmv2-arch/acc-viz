from __future__ import annotations

import numpy as np
import pytest

from src.desktop.plots.heatmap_canvas import (
    HeatmapCanvas,
    colorscale_to_cmap,
    nearest_cell,
    resolve_hover,
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


def _grid():
    # grid[x, y]; (1,0) is NaN to represent an interpolation gap.
    return np.array([[1.0, 2.0], [np.nan, 4.0]])


def test_resolve_hover_measured_point():
    text = resolve_hover(
        0.05, 0.0,
        grid=_grid(),
        hole_lookup={(0, 0): 1.5},
        ref_value=None,
        normalized=False,
    )
    assert text == "x=0, y=0\ng RMS=1.5000"


def test_resolve_hover_interpolated_cell():
    text = resolve_hover(
        1.0, 1.0,
        grid=_grid(),
        hole_lookup={},
        ref_value=None,
        normalized=False,
    )
    assert text == "x=1, y=1\nInterpoliert (g RMS)=4.0000"


def test_resolve_hover_nan_gap_returns_none():
    # cell (1, 0) is NaN and not a measured hole.
    assert resolve_hover(
        1.0, 0.0, grid=_grid(), hole_lookup={}, ref_value=None, normalized=False,
    ) is None


def test_resolve_hover_out_of_bounds_returns_none():
    assert resolve_hover(
        5.0, 0.0, grid=_grid(), hole_lookup={}, ref_value=None, normalized=False,
    ) is None
    assert resolve_hover(
        None, None, grid=_grid(), hole_lookup={}, ref_value=None, normalized=False,
    ) is None


def test_resolve_hover_reference_center_takes_priority():
    # 2x2 grid -> center at (0.5, 0.5); ref_value present.
    text = resolve_hover(
        0.5, 0.5,
        grid=_grid(),
        hole_lookup={(0, 0): 1.5},
        ref_value=0.8,
        normalized=False,
    )
    assert text == "Referenz (Mitte)\ng RMS=0.8000"


def test_resolve_hover_reference_none_falls_back_to_cell():
    # Near center but no reference -> snaps to a cell instead.
    text = resolve_hover(
        0.4, 0.4,
        grid=_grid(),
        hole_lookup={(0, 0): 1.5},
        ref_value=None,
        normalized=False,
    )
    assert text == "x=0, y=0\ng RMS=1.5000"


def test_resolve_hover_normalized_label():
    text = resolve_hover(
        1.0, 1.0,
        grid=_grid(),
        hole_lookup={},
        ref_value=None,
        normalized=True,
    )
    assert text == "x=1, y=1\nInterpoliert (Normalisiert)=4.0000"


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


def test_heatmap_canvas_motion_shows_tooltip(qapp):
    canvas = HeatmapCanvas()
    grid = np.array([[1.0, 2.0], [3.0, 4.0]])
    canvas.render_grid(
        grid, plate_name="Platte 1", title="t", colorscale="Viridis",
        normalized=False, hole_positions=[(0, 0)], hole_values=[1.5],
        ref_value=None, z_range=None,
    )

    class _Evt:
        inaxes = canvas.axes
        xdata = 0.0
        ydata = 0.0

    # Should not raise and should resolve the measured-hole tooltip text.
    canvas._on_motion(_Evt())
    assert canvas._last_hover == "x=0, y=0\ng RMS=1.5000"

    class _OutEvt:
        inaxes = None
        xdata = None
        ydata = None

    canvas._on_motion(_OutEvt())
    assert canvas._last_hover is None


def test_render_grid_all_nan_shows_empty_text(qapp):
    canvas = HeatmapCanvas()
    grid = np.full((3, 3), np.nan)
    canvas.render_grid(
        grid,
        plate_name="P1",
        title="P1",
        colorscale="Viridis",
        normalized=False,
        hole_positions=[],
        hole_values=[],
        ref_value=None,
        z_range=None,
    )
    texts = [t.get_text() for t in canvas.axes.texts]
    assert any("Frequenzband" in t for t in texts)


# --- selection marker layer -----------------------------------------------

def _render_basic(canvas: HeatmapCanvas, selected=()):
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
        z_range=None,
        selected=selected,
    )


def test_render_grid_without_selection_has_no_selection_artist(qapp):
    canvas = HeatmapCanvas()
    _render_basic(canvas)
    assert canvas._selection_artist is None


def test_render_grid_with_selection_draws_marker(qapp):
    canvas = HeatmapCanvas()
    _render_basic(canvas, selected=[(0, 0, "C0")])
    assert canvas._selection_artist is not None


def test_set_selected_updates_marker_layer(qapp):
    canvas = HeatmapCanvas()
    _render_basic(canvas)
    canvas.set_selected([(1, 1, "C1")])
    assert canvas._selection_artist is not None
    # Clearing removes the marker layer again.
    canvas.set_selected([])
    assert canvas._selection_artist is None
