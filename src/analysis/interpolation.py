from __future__ import annotations

"""Grid interpolation helpers used to fill missing heatmap cells."""

import numpy as np
from scipy.interpolate import griddata


def interpolate_grid(grid: np.ndarray, ref_value: float | None = None) -> np.ndarray:
    """Linearly interpolate NaNs and fall back to nearest-neighbour outside the hull.

    If ``ref_value`` is provided, it is injected at the geometric center of the
    grid to pull the interpolated surface toward that reference. The injection
    is skipped when the center coincides with an existing measurement, because
    a duplicate coordinate with a different value makes ``griddata``
    non-deterministic.

    Args:
        grid: 2D array of measured values with NaN for missing cells.
        ref_value: Optional reference value to inject at the grid center.

    Returns:
        A 2D array of the same shape as ``grid`` with NaN cells filled in. If
        fewer than three known points are available the input is returned
        unchanged (as a copy).
    """
    known_mask = ~np.isnan(grid)
    nrows, ncols = grid.shape
    rows, cols = np.mgrid[0:nrows, 0:ncols]

    pts_list = [np.column_stack([rows[known_mask], cols[known_mask]])]
    vals_list = [grid[known_mask]]
    if ref_value is not None:
        cy = (nrows - 1) / 2
        cx = (ncols - 1) / 2
        # Only inject when the center doesn't coincide with a real measurement;
        # a duplicate coordinate with a different value makes griddata non-deterministic.
        center_on_cell = np.logical_and(nrows % 2 == 1, ncols % 2 == 1)
        center_already_known = bool(center_on_cell) and bool(known_mask[int(cy), int(cx)])
        if not center_already_known:
            pts_list.append(np.array([[cy, cx]]))
            vals_list.append(np.array([ref_value]))

    points = np.vstack(pts_list)
    values = np.concatenate(vals_list)

    if len(points) < 3:
        return grid.copy()

    linear = griddata(points, values, (rows, cols), method="linear")
    nan_mask = np.isnan(linear)
    if nan_mask.any():
        nearest = griddata(points, values, (rows, cols), method="nearest")
        linear[nan_mask] = nearest[nan_mask]
    return linear
