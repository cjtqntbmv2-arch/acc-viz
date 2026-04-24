from __future__ import annotations

"""Assemble a 2D grid of per-hole band-RMS values for heatmap rendering."""

from typing import Literal

import numpy as np
import pandas as pd

from src.analysis.rms import compute_band_rms


def build_grid(
    hole_data: dict[tuple[int, int], pd.DataFrame],
    ref_df: pd.DataFrame | None,
    f_min: float,
    f_max: float,
    axis: Literal["X", "Y", "Z", "RSS"],
    normalize: bool,
) -> np.ndarray:
    """Build an ``(max_x, max_y)`` grid of band-RMS values, NaN where no data.

    For each hole position ``(x, y)`` present in ``hole_data``, computes the
    band-RMS of the chosen axis over ``[f_min, f_max]``. When ``normalize`` is
    true and a positive, finite reference RMS is available, each cell is
    divided by that reference value.

    Args:
        hole_data: Mapping from ``(x, y)`` hole coordinate (1-indexed) to the
            measurement DataFrame for that hole.
        ref_df: Optional reference DataFrame used for normalization.
        f_min: Lower bound of the frequency band in Hz.
        f_max: Upper bound of the frequency band in Hz.
        axis: Axis whose PSD column is used for the RMS computation. Accepts
            ``"X"``, ``"Y"``, ``"Z"``, or ``"RSS"`` (Root Sum of Squares over
            all three axes).
        normalize: If true, divide each cell by the reference band-RMS when it
            is positive and finite.

    Returns:
        A 2D array of shape ``(max_x, max_y)`` with NaN entries for missing
        holes. Returns a single-NaN ``(1, 1)`` array when ``hole_data`` is
        empty.
    """
    if not hole_data:
        return np.full((1, 1), np.nan)

    max_x = max(x for x, _ in hole_data)
    max_y = max(y for _, y in hole_data)
    grid = np.full((max_x, max_y), np.nan)

    ref_rms = compute_band_rms(ref_df, f_min, f_max, axis) if ref_df is not None else None
    use_norm = normalize and ref_rms is not None and np.isfinite(ref_rms) and ref_rms > 0

    for (x, y), df in hole_data.items():
        rms = compute_band_rms(df, f_min, f_max, axis)
        grid[x - 1, y - 1] = rms / ref_rms if use_norm else rms

    return grid
