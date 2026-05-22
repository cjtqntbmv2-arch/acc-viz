from __future__ import annotations

import numpy as np

from src.desktop.plots.histogram_canvas import HistogramCanvas
from src.desktop.plots.spectrum_canvas import SpectrumCanvas
from tests.core.conftest import make_df


# --- histogram -------------------------------------------------------------

def test_histogram_render_does_not_raise(qapp):
    canvas = HistogramCanvas()
    values = np.array([1.0, 2.0, 2.0, 3.0, np.nan, 4.0])
    canvas.render_values(values, bins=20, normalized=False, ref_value=2.5, x_range=(1.0, 4.0))
    assert len(canvas.axes.patches) > 0  # histogram bars present


def test_histogram_empty_input_renders_message(qapp):
    canvas = HistogramCanvas()
    values = np.array([np.nan, np.nan])
    canvas.render_values(values, bins=20, normalized=False, ref_value=None, x_range=None)
    assert len(canvas.axes.texts) >= 1  # "no data" annotation


# --- spectrum --------------------------------------------------------------

def _df():
    return make_df([0.0, 1.0, 2.0, 3.0, 4.0], 1e-3)


def test_spectrum_single_axis_one_line_without_ref(qapp):
    canvas = SpectrumCanvas()
    canvas.render_spectrum(
        plate_name="Platte 1", x_hole=0, y_hole=0, axis="X",
        hole_df=_df(), ref_df=None, f_min=0, f_max=2,
    )
    assert len(canvas.axes.get_lines()) == 1


def test_spectrum_single_axis_two_lines_with_ref(qapp):
    canvas = SpectrumCanvas()
    canvas.render_spectrum(
        plate_name="Platte 1", x_hole=0, y_hole=0, axis="X",
        hole_df=_df(), ref_df=_df(), f_min=0, f_max=2,
    )
    assert len(canvas.axes.get_lines()) == 2


def test_spectrum_rss_has_three_axes_plus_sum(qapp):
    canvas = SpectrumCanvas()
    canvas.render_spectrum(
        plate_name="Platte 1", x_hole=0, y_hole=0, axis="RSS",
        hole_df=_df(), ref_df=None, f_min=0, f_max=2,
    )
    assert len(canvas.axes.get_lines()) == 4  # X, Y, Z, sum


def test_spectrum_rss_with_ref_adds_ref_sum_line(qapp):
    canvas = SpectrumCanvas()
    canvas.render_spectrum(
        plate_name="Platte 1", x_hole=0, y_hole=0, axis="RSS",
        hole_df=_df(), ref_df=_df(), f_min=0, f_max=2,
    )
    assert len(canvas.axes.get_lines()) == 5  # X, Y, Z, sum, ref-sum


def test_spectrum_uses_log_y_axis(qapp):
    canvas = SpectrumCanvas()
    canvas.render_spectrum(
        plate_name="Platte 1", x_hole=0, y_hole=0, axis="X",
        hole_df=_df(), ref_df=None, f_min=0, f_max=2,
    )
    assert canvas.axes.get_yscale() == "log"
