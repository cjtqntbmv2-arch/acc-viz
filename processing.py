import math
import numpy as np
import pandas as pd


def compute_band_rms(df: pd.DataFrame, f_min: float, f_max: float, axis: str) -> float:
    col = f"PSD_{axis}_g2Hz"
    mask = (df["Frequenz_Hz"] >= f_min) & (df["Frequenz_Hz"] <= f_max)
    filtered = df.loc[mask, ["Frequenz_Hz", col]]
    if len(filtered) < 1:
        return math.nan
    # PSD data is uniformly spaced; estimate delta_f from first two points
    delta_f = (
        float(filtered["Frequenz_Hz"].iloc[1] - filtered["Frequenz_Hz"].iloc[0])
        if len(filtered) > 1
        else 1.0
    )
    return float(np.sqrt((filtered[col] * delta_f).sum()))


def build_grid(
    hole_data: dict[tuple[int, int], pd.DataFrame],
    ref_df: pd.DataFrame | None,
    f_min: float,
    f_max: float,
    axis: str,
    normalize: bool,
) -> np.ndarray:
    if not hole_data:
        return np.full((1, 1), np.nan)

    max_x = max(x for x, _ in hole_data)
    max_y = max(y for _, y in hole_data)
    grid = np.full((max_x, max_y), np.nan)

    ref_rms = compute_band_rms(ref_df, f_min, f_max, axis) if ref_df is not None else None

    for (x, y), df in hole_data.items():
        rms = compute_band_rms(df, f_min, f_max, axis)
        if normalize and ref_rms and ref_rms > 0:
            grid[x - 1, y - 1] = rms / ref_rms
        else:
            grid[x - 1, y - 1] = rms

    return grid
