from __future__ import annotations

import math
import pandas as pd
from src.analysis.rms import compute_band_rms


def _df(freqs, psd_x, psd_y=0.0, psd_z=0.0):
    return pd.DataFrame({
        "Frequenz_Hz": freqs,
        "PSD_X_g2Hz": [psd_x] * len(freqs) if not isinstance(psd_x, list) else psd_x,
        "PSD_Y_g2Hz": [psd_y] * len(freqs) if not isinstance(psd_y, list) else psd_y,
        "PSD_Z_g2Hz": [psd_z] * len(freqs) if not isinstance(psd_z, list) else psd_z,
    })


def test_compute_band_rms_full_range():
    df = _df([0.0, 1.0, 2.0, 3.0, 4.0], 1e-3)
    result = compute_band_rms(df, f_min=0.0, f_max=4.0, axis="X")
    assert math.isclose(result, math.sqrt(4e-3), rel_tol=1e-6)


def test_compute_band_rms_partial_range():
    df = _df([0.0, 1.0, 2.0, 3.0, 4.0], 1e-3)
    result = compute_band_rms(df, f_min=1.0, f_max=2.0, axis="X")
    assert math.isclose(result, math.sqrt(1e-3), rel_tol=1e-6)


def test_compute_band_rms_axis_selection():
    df = _df([0.0, 1.0, 2.0], 1e-3, 4e-3, 9e-3)
    assert math.isclose(compute_band_rms(df, 0.0, 2.0, "Y"), math.sqrt(2 * 4e-3), rel_tol=1e-6)
    assert math.isclose(compute_band_rms(df, 0.0, 2.0, "Z"), math.sqrt(2 * 9e-3), rel_tol=1e-6)


def test_compute_band_rms_band_outside_data_is_nan():
    df = _df([0.0, 1.0, 2.0], 1e-3)
    assert math.isnan(compute_band_rms(df, 10.0, 20.0, "X"))


def test_compute_band_rms_fmin_equals_fmax_is_nan():
    df = _df([0.0, 1.0, 2.0], 1e-3)
    assert math.isnan(compute_band_rms(df, 1.0, 1.0, "X"))


def test_compute_band_rms_single_point_in_band_is_nan():
    df = _df([0.0, 5.0, 10.0], 1e-3)
    assert math.isnan(compute_band_rms(df, 4.0, 6.0, "X"))


def test_compute_band_rms_all_nan_in_band_is_nan():
    df = pd.DataFrame({
        "Frequenz_Hz": [0.0, 1.0, 2.0],
        "PSD_X_g2Hz": [float("nan")] * 3,
        "PSD_Y_g2Hz": [0.0] * 3,
        "PSD_Z_g2Hz": [0.0] * 3,
    })
    assert math.isnan(compute_band_rms(df, 0.0, 2.0, "X"))


def test_compute_band_rms_rss_equals_pythagoras():
    df = _df([0.0, 1.0, 2.0], 1e-3, 4e-3, 4e-3)
    result = compute_band_rms(df, 0.0, 2.0, "RSS")
    assert math.isclose(result, math.sqrt(2 * (1e-3 + 4e-3 + 4e-3)), rel_tol=1e-6)


def test_compute_band_rms_rss_nan_axis_propagates():
    df = pd.DataFrame({
        "Frequenz_Hz": [0.0, 1.0, 2.0],
        "PSD_X_g2Hz": [1e-3] * 3,
        "PSD_Y_g2Hz": [float("nan")] * 3,
        "PSD_Z_g2Hz": [2e-3] * 3,
    })
    assert math.isnan(compute_band_rms(df, 0.0, 2.0, "RSS"))


def test_compute_band_rms_rss_band_outside_data_is_nan():
    df = _df([0.0, 1.0, 2.0], 1e-3, 2e-3, 3e-3)
    assert math.isnan(compute_band_rms(df, 10.0, 20.0, "RSS"))


def test_compute_band_rms_rss_equals_sum_of_axis_squares():
    df = _df([0.0, 1.0, 2.0, 3.0, 4.0], 7e-4, 2.5e-3, 9e-3)
    rmx = compute_band_rms(df, 1.0, 3.0, "X")
    rmy = compute_band_rms(df, 1.0, 3.0, "Y")
    rmz = compute_band_rms(df, 1.0, 3.0, "Z")
    rss = compute_band_rms(df, 1.0, 3.0, "RSS")
    assert math.isclose(rss, math.sqrt(rmx**2 + rmy**2 + rmz**2), rel_tol=1e-6)
