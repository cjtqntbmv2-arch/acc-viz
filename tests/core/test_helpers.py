from __future__ import annotations

import math

import numpy as np

from src.core.colorscales import COLORSCALES, to_cmap
from src.core.pipeline import measured_points, ref_marker
from src.core.settings import normalize_path


def test_to_cmap_known_and_unknown():
    assert to_cmap("Viridis") == "viridis"
    assert to_cmap("RdBu") == "RdBu"
    assert to_cmap("does-not-exist") == "viridis"


def test_colorscales_all_map():
    assert all(to_cmap(name) for name in COLORSCALES)


def test_normalize_path():
    assert normalize_path('  "/a/b" ') == "/a/b"
    assert normalize_path("'/x'") == "/x"
    assert normalize_path("") == ""


def test_measured_points_filters_nan():
    grid = np.array([[1.0, np.nan], [3.0, 4.0]])
    hole_data = {(0, 0): None, (0, 1): None, (1, 1): None}
    positions, values = measured_points(grid, hole_data)
    assert (0, 0) in positions and (1, 1) in positions
    assert (0, 1) not in positions  # NaN value filtered out
    assert all(not math.isnan(v) for v in values)
    assert len(positions) == len(values)


def test_ref_marker_rule():
    assert ref_marker(None, normalize=False) is None
    assert ref_marker(None, normalize=True) is None
    assert ref_marker(2.5, normalize=False) == 2.5
    assert ref_marker(2.5, normalize=True) == 1.0
