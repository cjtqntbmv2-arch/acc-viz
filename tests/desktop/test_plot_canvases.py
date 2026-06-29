from __future__ import annotations

import numpy as np

from src.desktop.plots.histogram_canvas import HistogramCanvas
from src.desktop.plots.spectrum_canvas import SpectrumCanvas, SpectrumPoint
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


def test_histogram_stats_overlay_draws_lines_and_legend(qapp):
    canvas = HistogramCanvas()
    values = np.array([1.0, 2.0, 2.0, 3.0, np.nan, 4.0])
    canvas.render_values(values, bins=20, normalized=False, show_stats=True)
    # mean, median, -1σ, +1σ → four vertical stat lines
    assert len(canvas.axes.get_lines()) == 4
    assert canvas.axes.get_legend() is not None


def test_histogram_stats_overlay_off_by_default(qapp):
    canvas = HistogramCanvas()
    values = np.array([1.0, 2.0, 2.0, 3.0, 4.0])
    canvas.render_values(values, bins=20, normalized=False)
    assert len(canvas.axes.get_lines()) == 0
    assert canvas.axes.get_legend() is None


def test_histogram_stats_single_value_draws_no_sigma(qapp):
    canvas = HistogramCanvas()
    values = np.array([2.0, np.nan])
    canvas.render_values(values, bins=20, normalized=False, show_stats=True)
    # too few points for a meaningful spread → no stat lines, no raise
    assert len(canvas.axes.get_lines()) == 0


# --- spectrum --------------------------------------------------------------

def _df():
    return make_df([0.0, 1.0, 2.0, 3.0, 4.0], 1e-3)


def _point(ref=None, color=None):
    return SpectrumPoint(
        plate_name="Platte 1", x_hole=0, y_hole=0,
        hole_df=_df(), ref_df=ref, color=color,
    )


def test_spectrum_single_axis_one_line_without_ref(qapp):
    canvas = SpectrumCanvas()
    canvas.render_spectrum([_point()], axis="X", f_min=0, f_max=2)
    assert len(canvas.axes.get_lines()) == 1


def test_spectrum_single_axis_two_lines_with_ref(qapp):
    canvas = SpectrumCanvas()
    canvas.render_spectrum([_point(ref=_df())], axis="X", f_min=0, f_max=2)
    assert len(canvas.axes.get_lines()) == 2  # hole + ref


def test_spectrum_rss_single_point_only_sum_line(qapp):
    canvas = SpectrumCanvas()
    canvas.render_spectrum([_point()], axis="RSS", f_min=0, f_max=2)
    # Nur die RSS-Summenkurve, keine X/Y/Z-Einzellinien mehr.
    assert len(canvas.axes.get_lines()) == 1


def test_spectrum_rss_single_point_with_ref_adds_ref_sum(qapp):
    canvas = SpectrumCanvas()
    canvas.render_spectrum([_point(ref=_df())], axis="RSS", f_min=0, f_max=2)
    assert len(canvas.axes.get_lines()) == 2  # sum + ref-sum


def test_spectrum_multiple_points_one_line_each_no_ref(qapp):
    canvas = SpectrumCanvas()
    p0 = SpectrumPoint("Platte 1", 0, 0, _df(), _df(), "C0")
    p1 = SpectrumPoint("Platte 2", 1, 1, _df(), _df(), "C1")
    canvas.render_spectrum([p0, p1], axis="X", f_min=0, f_max=2)
    # Zwei Punkte => zwei Linien, Referenz bei Mehrfachauswahl unterdrückt.
    assert len(canvas.axes.get_lines()) == 2


def test_spectrum_uses_log_y_axis(qapp):
    canvas = SpectrumCanvas()
    canvas.render_spectrum([_point()], axis="X", f_min=0, f_max=2)
    assert canvas.axes.get_yscale() == "log"


def test_spectrum_empty_points_does_not_raise(qapp):
    canvas = SpectrumCanvas()
    canvas.render_spectrum([], axis="X", f_min=0, f_max=2)
    assert len(canvas.axes.get_lines()) == 0
