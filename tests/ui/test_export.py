from __future__ import annotations

import io
import math
import pandas as pd

from src.ui.export import build_export_dataframe


def _df(val):
    return pd.DataFrame({
        "Frequenz_Hz": [0.0, 1.0, 2.0],
        "PSD_X_g2Hz": [val] * 3,
        "PSD_Y_g2Hz": [val] * 3,
        "PSD_Z_g2Hz": [val] * 3,
    })


def test_export_contains_all_holes_and_plates():
    plates = {
        "Platte 1": ({(1, 1): _df(1e-3), (1, 2): _df(2e-3)}, _df(1e-3)),
        "Platte 2": ({(1, 1): _df(4e-3)}, None),
    }
    df = build_export_dataframe(plates, f_min=0, f_max=2, axis="X")
    assert set(df["plate"]) == {"Platte 1", "Platte 2"}
    assert len(df) == 3


def test_export_normalization_column_filled_when_ref_present():
    plates = {
        "Platte 1": ({(1, 1): _df(4e-3)}, _df(1e-3)),
    }
    df = build_export_dataframe(plates, f_min=0, f_max=2, axis="X")
    row = df.iloc[0]
    assert math.isclose(float(row["band_rms_normalized"]), 2.0, rel_tol=1e-6)


def test_export_normalization_nan_when_no_ref():
    plates = {"Platte 1": ({(1, 1): _df(4e-3)}, None)}
    df = build_export_dataframe(plates, f_min=0, f_max=2, axis="X")
    assert math.isnan(float(df.iloc[0]["band_rms_normalized"]))


def test_export_normalization_nan_when_ref_zero():
    plates = {"Platte 1": ({(1, 1): _df(4e-3)}, _df(0.0))}
    df = build_export_dataframe(plates, f_min=0, f_max=2, axis="X")
    assert math.isnan(float(df.iloc[0]["band_rms_normalized"]))


def test_export_nan_when_hole_rms_nan():
    empty = pd.DataFrame({
        "Frequenz_Hz": [0.0],
        "PSD_X_g2Hz": [1e-3],
        "PSD_Y_g2Hz": [1e-3],
        "PSD_Z_g2Hz": [1e-3],
    })
    plates = {"Platte 1": ({(1, 1): empty}, _df(1e-3))}
    df = build_export_dataframe(plates, f_min=0, f_max=2, axis="X")
    assert math.isnan(float(df.iloc[0]["band_rms_abs"]))
    assert math.isnan(float(df.iloc[0]["band_rms_normalized"]))


def test_export_axis_rss_sets_column_value():
    plates = {"Platte 1": ({(1, 1): _df(1e-3)}, _df(1e-3))}
    df = build_export_dataframe(plates, f_min=0, f_max=2, axis="RSS")
    assert list(df["axis"]) == ["RSS"] * len(df)
    assert not math.isnan(float(df.iloc[0]["band_rms_abs"]))


def test_export_axis_rss_pythagoras():
    hole = pd.DataFrame({
        "Frequenz_Hz": [0.0, 1.0, 2.0],
        "PSD_X_g2Hz": [1e-3] * 3,
        "PSD_Y_g2Hz": [4e-3] * 3,
        "PSD_Z_g2Hz": [4e-3] * 3,
    })
    plates = {"Platte 1": ({(1, 1): hole}, None)}
    df = build_export_dataframe(plates, f_min=0, f_max=2, axis="RSS")
    row = df.iloc[0]
    expected = math.sqrt(2 * (1e-3 + 4e-3 + 4e-3))
    assert math.isclose(float(row["band_rms_abs"]), expected, rel_tol=1e-6)
    assert math.isnan(float(row["band_rms_normalized"]))
