import math
import numpy as np
import pandas as pd
from processing import compute_band_rms, build_grid


def make_df(freqs, psd_x, psd_y, psd_z):
    return pd.DataFrame({
        "Frequenz_Hz": freqs,
        "PSD_X_g2Hz": psd_x,
        "PSD_Y_g2Hz": psd_y,
        "PSD_Z_g2Hz": psd_z,
    })


def test_compute_band_rms_full_range():
    # 5 points at 1 Hz spacing, PSD_X = 1e-3
    # delta_f=1.0, sum = 5 * 1e-3, rms = sqrt(5e-3)
    df = make_df([0.0, 1.0, 2.0, 3.0, 4.0], 1e-3, 2e-3, 3e-3)
    result = compute_band_rms(df, f_min=0.0, f_max=4.0, axis="X")
    assert math.isclose(result, math.sqrt(5e-3), rel_tol=1e-6)


def test_compute_band_rms_partial_range():
    # Points 1.0 and 2.0 in [1.0, 2.0]: sum = 2 * 1e-3, rms = sqrt(2e-3)
    df = make_df([0.0, 1.0, 2.0, 3.0, 4.0], 1e-3, 2e-3, 3e-3)
    result = compute_band_rms(df, f_min=1.0, f_max=2.0, axis="X")
    assert math.isclose(result, math.sqrt(2e-3), rel_tol=1e-6)


def test_compute_band_rms_axis_y():
    df = make_df([0.0, 1.0, 2.0], 1e-3, 4e-3, 9e-3)
    result = compute_band_rms(df, f_min=0.0, f_max=2.0, axis="Y")
    assert math.isclose(result, math.sqrt(3 * 4e-3), rel_tol=1e-6)


def test_compute_band_rms_axis_z():
    df = make_df([0.0, 1.0, 2.0], 1e-3, 4e-3, 9e-3)
    result = compute_band_rms(df, f_min=0.0, f_max=2.0, axis="Z")
    assert math.isclose(result, math.sqrt(3 * 9e-3), rel_tol=1e-6)


def test_compute_band_rms_empty_range():
    df = make_df([0.0, 1.0, 2.0], 1e-3, 2e-3, 3e-3)
    result = compute_band_rms(df, f_min=10.0, f_max=20.0, axis="X")
    assert math.isnan(result)


def test_build_grid_shape():
    hole_data = {
        (1, 1): make_df([0.0, 1.0, 2.0], 1e-3, 2e-3, 3e-3),
        (1, 2): make_df([0.0, 1.0, 2.0], 2e-3, 4e-3, 6e-3),
        (2, 1): make_df([0.0, 1.0, 2.0], 4e-3, 8e-3, 12e-3),
    }
    grid = build_grid(hole_data, None, 0.0, 2.0, "X", normalize=False)
    assert grid.shape == (2, 2)


def test_build_grid_missing_hole_is_nan():
    hole_data = {
        (1, 1): make_df([0.0, 1.0, 2.0], 1e-3, 2e-3, 3e-3),
        (1, 2): make_df([0.0, 1.0, 2.0], 2e-3, 4e-3, 6e-3),
        (2, 1): make_df([0.0, 1.0, 2.0], 4e-3, 8e-3, 12e-3),
    }
    grid = build_grid(hole_data, None, 0.0, 2.0, "X", normalize=False)
    assert math.isnan(grid[1, 1])  # (2,2) missing


def test_build_grid_values_abs():
    hole_data = {
        (1, 1): make_df([0.0, 1.0, 2.0], 1e-3, 2e-3, 3e-3),
    }
    grid = build_grid(hole_data, None, 0.0, 2.0, "X", normalize=False)
    assert math.isclose(grid[0, 0], math.sqrt(3e-3), rel_tol=1e-6)


def test_build_grid_normalized():
    # ref rms_X = sqrt(3 * 1e-3); hole rms_X = sqrt(3 * 4e-3); ratio = 2.0
    ref_df = make_df([0.0, 1.0, 2.0], 1e-3, 2e-3, 3e-3)
    hole_data = {
        (1, 1): make_df([0.0, 1.0, 2.0], 4e-3, 8e-3, 12e-3),
    }
    grid = build_grid(hole_data, ref_df, 0.0, 2.0, "X", normalize=True)
    assert math.isclose(grid[0, 0], 2.0, rel_tol=1e-6)


def test_build_grid_empty_returns_nan_grid():
    grid = build_grid({}, None, 0.0, 2.0, "X", normalize=False)
    assert grid.shape == (1, 1)
    assert math.isnan(grid[0, 0])


from processing import interpolate_grid


def test_interpolate_grid_fills_interior():
    # 3x3 Grid: Werte an allen 4 Ecken, Mitte und Kanten fehlen
    # Linear interpoliert: Zentrum (1,1) soll ~2.0 sein (Mittel der Ecken)
    grid = np.array([
        [1.0, np.nan, 3.0],
        [np.nan, np.nan, np.nan],
        [1.0, np.nan, 3.0],
    ])
    result = interpolate_grid(grid)
    assert not np.isnan(result[1, 1])
    assert np.isclose(result[1, 1], 2.0, atol=0.1)


def test_interpolate_grid_preserves_known_values():
    grid = np.array([
        [1.0, np.nan, 3.0],
        [np.nan, np.nan, np.nan],
        [1.0, np.nan, 3.0],
    ])
    result = interpolate_grid(grid)
    assert np.isclose(result[0, 0], 1.0)
    assert np.isclose(result[0, 2], 3.0)


def test_interpolate_grid_outside_convex_hull_is_nan():
    # Nur 3 Punkte im Zentrum — Ecken liegen außerhalb der konvexen Hülle
    grid = np.full((5, 5), np.nan)
    grid[2, 1] = 1.0
    grid[2, 3] = 2.0
    grid[3, 2] = 3.0
    result = interpolate_grid(grid)
    assert np.isnan(result[0, 0])
    assert np.isnan(result[4, 4])


def test_interpolate_grid_too_few_points_returns_copy():
    # Weniger als 3 Messpunkte: keine Interpolation möglich, Grid unverändert zurück
    grid = np.full((3, 3), np.nan)
    grid[1, 1] = 5.0
    result = interpolate_grid(grid)
    assert np.isclose(result[1, 1], 5.0)
    assert np.isnan(result[0, 0])


def test_interpolate_grid_no_nan_unchanged():
    # Vollständig befülltes Grid bleibt unverändert
    grid = np.array([[1.0, 2.0], [3.0, 4.0]])
    result = interpolate_grid(grid)
    assert np.allclose(result, grid)
