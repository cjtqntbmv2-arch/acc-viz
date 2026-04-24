from __future__ import annotations

import math
import pandas as pd
from src.analysis.grid import build_grid


def _df(freqs, val):
    return pd.DataFrame({
        "Frequenz_Hz": freqs,
        "PSD_X_g2Hz": [val] * len(freqs),
        "PSD_Y_g2Hz": [val] * len(freqs),
        "PSD_Z_g2Hz": [val] * len(freqs),
    })


def test_build_grid_shape_from_max_xy():
    holes = {
        (1, 1): _df([0.0, 1.0, 2.0], 1e-3),
        (1, 2): _df([0.0, 1.0, 2.0], 1e-3),
        (2, 1): _df([0.0, 1.0, 2.0], 1e-3),
    }
    g = build_grid(holes, None, 0.0, 2.0, "X", normalize=False)
    assert g.shape == (2, 2)


def test_build_grid_missing_hole_is_nan():
    holes = {(1, 1): _df([0.0, 1.0, 2.0], 1e-3), (2, 2): _df([0.0, 1.0, 2.0], 1e-3)}
    g = build_grid(holes, None, 0.0, 2.0, "X", normalize=False)
    assert math.isnan(g[0, 1])
    assert math.isnan(g[1, 0])


def test_build_grid_absolute_value():
    holes = {(1, 1): _df([0.0, 1.0, 2.0], 1e-3)}
    g = build_grid(holes, None, 0.0, 2.0, "X", normalize=False)
    assert math.isclose(g[0, 0], math.sqrt(2e-3), rel_tol=1e-6)


def test_build_grid_normalized_against_reference():
    ref = _df([0.0, 1.0, 2.0], 1e-3)
    holes = {(1, 1): _df([0.0, 1.0, 2.0], 4e-3)}
    g = build_grid(holes, ref, 0.0, 2.0, "X", normalize=True)
    assert math.isclose(g[0, 0], 2.0, rel_tol=1e-6)


def test_build_grid_normalize_without_ref_uses_absolute():
    holes = {(1, 1): _df([0.0, 1.0, 2.0], 4e-3)}
    g = build_grid(holes, None, 0.0, 2.0, "X", normalize=True)
    assert math.isclose(g[0, 0], math.sqrt(2 * 4e-3), rel_tol=1e-6)


def test_build_grid_empty_returns_nan_1x1():
    g = build_grid({}, None, 0.0, 2.0, "X", normalize=False)
    assert g.shape == (1, 1)
    assert math.isnan(g[0, 0])


def test_build_grid_ref_rms_zero_falls_back_to_absolute():
    ref = _df([0.0, 1.0, 2.0], 0.0)
    holes = {(1, 1): _df([0.0, 1.0, 2.0], 4e-3)}
    g = build_grid(holes, ref, 0.0, 2.0, "X", normalize=True)
    assert math.isclose(g[0, 0], math.sqrt(2 * 4e-3), rel_tol=1e-6)
