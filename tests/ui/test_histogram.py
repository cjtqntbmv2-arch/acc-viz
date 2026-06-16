from __future__ import annotations

import numpy as np
import plotly.graph_objects as go

from src.ui.histogram import _INTEGER_TICK_THRESHOLD, make_histogram


def test_make_histogram_returns_figure_with_bar_trace():
    rng = np.random.default_rng(0)
    values = rng.uniform(0.0, 5.0, 5)
    fig = make_histogram(values, bins=5, normalized=False)
    bar_traces = [t for t in fig.data if isinstance(t, go.Bar)]
    assert len(bar_traces) >= 1


def test_make_histogram_respects_bins():
    rng = np.random.default_rng(1)
    values = rng.uniform(0.0, 5.0, 50)
    fig = make_histogram(values, bins=10, normalized=False)
    bar_traces = [t for t in fig.data if isinstance(t, go.Bar)]
    assert len(bar_traces) == 1
    y = list(bar_traces[0].y)  # type: ignore[arg-type]
    assert len(y) == 10


def test_make_histogram_auto_caps_bins_to_data_size():
    values = np.array([1.0, 2.0, 3.0])
    fig = make_histogram(values, bins=20, normalized=False)
    bar_traces = [t for t in fig.data if isinstance(t, go.Bar)]
    assert len(bar_traces) == 1
    y = list(bar_traces[0].y)  # type: ignore[arg-type]
    assert len(y) == 3


def test_make_histogram_empty_input_returns_figure_without_bar():
    values = np.array([np.nan, np.nan, np.nan])
    fig = make_histogram(values, bins=10, normalized=False)
    bar_traces = [t for t in fig.data if isinstance(t, go.Bar)]
    assert len(bar_traces) == 0
    assert len(fig.layout.annotations) >= 1  # type: ignore[reportAttributeAccessIssue]


def test_make_histogram_single_value():
    values = np.array([1.5])
    fig = make_histogram(values, bins=20, normalized=False)
    bar_traces = [t for t in fig.data if isinstance(t, go.Bar)]
    assert len(bar_traces) == 1
    y = list(bar_traces[0].y)  # type: ignore[arg-type]
    assert len(y) == 1
    assert int(y[0]) == 1


def test_make_histogram_axis_label_changes_with_normalized():
    values = np.array([1.0, 2.0, 3.0])
    fig_norm = make_histogram(values, bins=5, normalized=True)
    fig_abs = make_histogram(values, bins=5, normalized=False)
    assert "Normalisiert" in fig_norm.layout.xaxis.title.text  # type: ignore[reportAttributeAccessIssue]
    assert "g RMS" in fig_abs.layout.xaxis.title.text  # type: ignore[reportAttributeAccessIssue]


def test_make_histogram_ref_value_adds_vline():
    values = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
    fig = make_histogram(values, bins=5, normalized=False, ref_value=1.0)
    assert len(fig.layout.shapes) >= 1  # type: ignore[reportAttributeAccessIssue]


def test_make_histogram_x_range_applied():
    values = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
    fig = make_histogram(values, bins=5, normalized=False, x_range=(0.0, 5.0))
    assert list(fig.layout.xaxis.range) == [0.0, 5.0]  # type: ignore[reportAttributeAccessIssue]


def test_make_histogram_integer_y_ticks_for_small_counts():
    # 3 values → counts will be ≤ _INTEGER_TICK_THRESHOLD
    values = np.array([1.0, 2.0, 3.0])
    assert len(values) <= _INTEGER_TICK_THRESHOLD
    fig = make_histogram(values, bins=3, normalized=False)
    assert fig.layout.yaxis.dtick == 1  # type: ignore[reportAttributeAccessIssue]


def test_make_histogram_show_stats_adds_stat_lines():
    values = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
    fig = make_histogram(values, bins=5, normalized=False, show_stats=True)
    # mean, median, -1σ, +1σ => mindestens 4 vertikale Linien (Shapes)
    assert len(fig.layout.shapes) >= 4  # type: ignore[reportAttributeAccessIssue]


def test_make_histogram_show_stats_default_off():
    values = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
    fig = make_histogram(values, bins=5, normalized=False)
    assert len(fig.layout.shapes) == 0  # type: ignore[reportAttributeAccessIssue]
