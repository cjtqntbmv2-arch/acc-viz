from __future__ import annotations

import math
import numpy as np
import pandas as pd


def compute_band_rms(df: pd.DataFrame, f_min: float, f_max: float, axis: str) -> float:
    """Compute sqrt(integral of PSD over [f_min, f_max]) for the given axis.
    Returns NaN if fewer than 2 valid data points fall inside the band.
    """
    if f_min >= f_max:
        return math.nan
    col = f"PSD_{axis}_g2Hz"
    mask = (df["Frequenz_Hz"] >= f_min) & (df["Frequenz_Hz"] <= f_max)
    sub = df.loc[mask, ["Frequenz_Hz", col]].sort_values("Frequenz_Hz").dropna()
    if len(sub) < 2:
        return math.nan
    return float(np.sqrt(np.trapezoid(sub[col].to_numpy(), sub["Frequenz_Hz"].to_numpy())))
