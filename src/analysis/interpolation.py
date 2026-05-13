from __future__ import annotations

"""Grid interpolation helpers used to fill missing heatmap cells."""

from typing import Literal

import numpy as np
from scipy.interpolate import RBFInterpolator, griddata

InterpolationMethod = Literal["linear", "tps"]


def interpolate_grid(
    grid: np.ndarray,
    ref_value: float | None = None,
    method: InterpolationMethod = "linear",
) -> np.ndarray:
    """Fill NaN cells in ``grid`` using the selected interpolation method.

    Args:
        grid: 2D array of measured values with NaN for missing cells.
        ref_value: Optional reference value injected at the geometric center
            to anchor the interpolated surface.
        method: ``"linear"`` (default) uses Delaunay triangulation with a
            nearest-neighbour fallback outside the convex hull.
            ``"tps"`` uses a thin-plate-spline RBF interpolator, producing a
            smooth surface that also handles collinear point sets.

    Returns:
        A 2D array of the same shape as ``grid`` with NaN cells filled in. If
        fewer than three known points are available the input is returned
        unchanged (as a copy).
    """
    points, values = _collect_known_points(grid, ref_value)
    if len(points) < 3:
        return grid.copy()

    nrows, ncols = grid.shape
    rows, cols = np.mgrid[0:nrows, 0:ncols]

    if method == "tps":
        return _interpolate_tps(points, values, rows, cols)
    if method == "linear":
        return _interpolate_linear(points, values, rows, cols)
    raise ValueError(
        f"Unknown interpolation method: {method!r}. Expected 'linear' or 'tps'."
    )


def _collect_known_points(
    grid: np.ndarray,
    ref_value: float | None,
) -> tuple[np.ndarray, np.ndarray]:
    """Stack measured points and the optional center reference."""
    known_mask = ~np.isnan(grid)
    nrows, ncols = grid.shape
    rows, cols = np.mgrid[0:nrows, 0:ncols]

    pts_list = [np.column_stack([rows[known_mask], cols[known_mask]])]
    vals_list = [grid[known_mask]]

    if ref_value is not None:
        cy = (nrows - 1) / 2
        cx = (ncols - 1) / 2
        # A duplicate coordinate with a different value makes the interpolators
        # non-deterministic — skip injection when the center is a real measurement.
        center_on_cell = bool(nrows % 2 == 1 and ncols % 2 == 1)
        center_already_known = center_on_cell and bool(known_mask[int(cy), int(cx)])
        if not center_already_known:
            pts_list.append(np.array([[cy, cx]]))
            vals_list.append(np.array([ref_value]))

    return np.vstack(pts_list), np.concatenate(vals_list)


def _interpolate_linear(
    points: np.ndarray,
    values: np.ndarray,
    rows: np.ndarray,
    cols: np.ndarray,
) -> np.ndarray:
    """Delaunay-linear interpolation with nearest-neighbour fallback."""
    linear = griddata(points, values, (rows, cols), method="linear")
    nan_mask = np.isnan(linear)
    if nan_mask.any():
        nearest = griddata(points, values, (rows, cols), method="nearest")
        linear[nan_mask] = nearest[nan_mask]
    return linear


def _interpolate_tps(
    points: np.ndarray,
    values: np.ndarray,
    rows: np.ndarray,
    cols: np.ndarray,
) -> np.ndarray:
    """Thin-plate-spline RBF interpolation (smooth, no hull boundary)."""
    interp = RBFInterpolator(points, values, kernel="thin_plate_spline", smoothing=0.0)
    query = np.column_stack([rows.ravel(), cols.ravel()])
    return interp(query).reshape(rows.shape)
