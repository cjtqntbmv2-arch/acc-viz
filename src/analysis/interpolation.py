from __future__ import annotations

import numpy as np
from scipy.interpolate import griddata


def interpolate_grid(grid: np.ndarray, ref_value: float | None = None) -> np.ndarray:
    """Linearly interpolate NaNs; fill any remaining NaNs via nearest-neighbour.
    If ref_value is provided, it is injected at the geometric center."""
    known_mask = ~np.isnan(grid)
    nrows, ncols = grid.shape
    rows, cols = np.mgrid[0:nrows, 0:ncols]

    pts_list = [np.column_stack([rows[known_mask], cols[known_mask]])]
    vals_list = [grid[known_mask]]
    if ref_value is not None:
        pts_list.append(np.array([[(nrows - 1) / 2, (ncols - 1) / 2]]))
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
