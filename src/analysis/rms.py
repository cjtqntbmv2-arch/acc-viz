from __future__ import annotations

"""Band-limited RMS computation from power spectral density data."""

import math
from typing import Literal

import numpy as np
import pandas as pd

Axis = Literal["X", "Y", "Z", "RSS"]


def _integrand_series(df: pd.DataFrame, axis: Axis) -> pd.Series:
    """Return the PSD series to integrate for the requested axis.

    For single axes (``"X"``, ``"Y"``, ``"Z"``) the matching
    ``PSD_{axis}_g2Hz`` column is returned unchanged. For ``"RSS"`` the
    per-frequency sum ``PSD_X + PSD_Y + PSD_Z`` is returned. Because the
    addition is performed via pandas without ``fillna``, any NaN on one of
    the three axes at a given frequency propagates to the summed series and
    will be removed by the common ``dropna()`` step in the caller.

    Args:
        df: DataFrame containing the PSD columns.
        axis: Requested axis identifier.

    Returns:
        A ``pd.Series`` aligned with ``df`` holding the integrand values.
    """
    if axis == "RSS":
        return df["PSD_X_g2Hz"] + df["PSD_Y_g2Hz"] + df["PSD_Z_g2Hz"]
    return df[f"PSD_{axis}_g2Hz"]


def compute_band_rms(
    df: pd.DataFrame,
    f_min: float,
    f_max: float,
    axis: Axis,
) -> float:
    """Compute ``sqrt(integral of PSD over [f_min, f_max])`` for the given axis.

    For a single axis (``"X"``, ``"Y"`` or ``"Z"``) the column
    ``PSD_{axis}_g2Hz`` is integrated with the trapezoidal rule over the
    frequency values that fall inside the band.

    For ``axis == "RSS"`` the three PSD columns are first summed per
    frequency (``PSD_X + PSD_Y + PSD_Z``) and the trapezoidal integration is
    then applied to this summed series. This is mathematically equivalent to
    ``sqrt(gRMS_X**2 + gRMS_Y**2 + gRMS_Z**2)``. NaN handling stays
    identical to the single-axis case: a NaN in any of the three axes at a
    given frequency propagates into the summed integrand and that row is
    dropped via ``dropna()`` before integration.

    Args:
        df: DataFrame containing at least ``Frequenz_Hz`` and the PSD columns
            needed for the requested axis. For ``"RSS"`` all three PSD
            columns (``PSD_X_g2Hz``, ``PSD_Y_g2Hz``, ``PSD_Z_g2Hz``) must be
            present.
        f_min: Lower band edge in Hz (inclusive).
        f_max: Upper band edge in Hz (inclusive).
        axis: Axis whose PSD to integrate. Use ``"RSS"`` to integrate the
            per-frequency sum of all three axis PSDs.

    Returns:
        The band-limited RMS as a float. Returns ``nan`` when ``f_min >=
        f_max`` or when fewer than two valid data points fall inside the
        band (after dropping NaN rows of the selected integrand).
    """
    if f_min >= f_max:
        return math.nan

    integrand = _integrand_series(df, axis)
    sub = (
        pd.DataFrame({"Frequenz_Hz": df["Frequenz_Hz"], "integrand": integrand})
        .loc[(df["Frequenz_Hz"] >= f_min) & (df["Frequenz_Hz"] <= f_max)]
        .sort_values("Frequenz_Hz")
        .dropna()
    )
    if len(sub) < 2:
        return math.nan
    return float(
        np.sqrt(np.trapezoid(sub["integrand"].to_numpy(), sub["Frequenz_Hz"].to_numpy()))
    )
