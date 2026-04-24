from __future__ import annotations

import numpy as np
import pandas as pd

from src.analysis.rms import compute_band_rms


def build_grid(
    hole_data: dict[tuple[int, int], pd.DataFrame],
    ref_df: pd.DataFrame | None,
    f_min: float,
    f_max: float,
    axis: str,
    normalize: bool,
) -> np.ndarray:
    """Build an (max_x, max_y) grid of band-RMS values, NaN where no data."""
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
