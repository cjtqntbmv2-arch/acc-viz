from __future__ import annotations

import numpy as np
from src.analysis.interpolation import interpolate_grid


def test_fills_interior_linearly():
    grid = np.array([
        [1.0, np.nan, 3.0],
        [np.nan, np.nan, np.nan],
        [1.0, np.nan, 3.0],
    ])
    result = interpolate_grid(grid)
    assert not np.isnan(result[1, 1])
    assert np.isclose(result[1, 1], 2.0, atol=0.1)


def test_preserves_known_values():
    grid = np.array([
        [1.0, np.nan, 3.0],
        [np.nan, np.nan, np.nan],
        [1.0, np.nan, 3.0],
    ])
    result = interpolate_grid(grid)
    assert np.isclose(result[0, 0], 1.0)
    assert np.isclose(result[0, 2], 3.0)


def test_outside_convex_hull_filled_by_nearest():
    grid = np.full((5, 5), np.nan)
    grid[2, 1] = 1.0
    grid[2, 3] = 2.0
    grid[3, 2] = 3.0
    result = interpolate_grid(grid)
    # No NaNs should remain — nearest fills outside the hull.
    assert not np.isnan(result).any()


def test_too_few_points_returns_copy():
    grid = np.full((3, 3), np.nan)
    grid[1, 1] = 5.0
    result = interpolate_grid(grid)
    assert np.isclose(result[1, 1], 5.0)
    assert np.isnan(result[0, 0])


def test_no_nan_unchanged():
    grid = np.array([[1.0, 2.0], [3.0, 4.0]])
    result = interpolate_grid(grid)
    assert np.allclose(result, grid)


def test_reference_value_used_at_center():
    grid = np.full((3, 3), np.nan)
    grid[0, 0] = 1.0
    grid[0, 2] = 1.0
    grid[2, 0] = 1.0
    grid[2, 2] = 1.0
    result = interpolate_grid(grid, ref_value=5.0)
    # Center should be pulled toward the reference value.
    assert result[1, 1] > 1.0
