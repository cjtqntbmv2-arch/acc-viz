from __future__ import annotations

import pandas as pd

from src.core.export import build_export_dataframe, export_csv_bytes
from src.desktop.export import save_export


def _df(val):
    return pd.DataFrame({
        "Frequenz_Hz": [0.0, 1.0, 2.0],
        "PSD_X_g2Hz": [val] * 3,
        "PSD_Y_g2Hz": [val] * 3,
        "PSD_Z_g2Hz": [val] * 3,
    })


def _plates():
    return {"Platte 1": ({(0, 0): _df(1e-3), (1, 1): _df(4e-3)}, _df(1e-3))}


def test_core_export_module_reexported_from_ui():
    from src.ui.export import build_export_dataframe as ui_fn

    assert ui_fn is build_export_dataframe


def test_export_csv_bytes_uses_semicolon_and_bom():
    data = export_csv_bytes(_plates(), f_min=0, f_max=2, axis="X")
    assert data.startswith(b"\xef\xbb\xbf")  # UTF-8 BOM
    text = data.decode("utf-8-sig")
    assert ";" in text.splitlines()[0]
    assert "band_rms_abs" in text


def test_save_export_writes_file(tmp_path):
    out = tmp_path / "export.csv"
    save_export(_plates(), str(out), f_min=0, f_max=2, axis="X")
    assert out.exists()
    df = pd.read_csv(out, sep=";", encoding="utf-8-sig")
    assert {"plate", "x", "y", "band_rms_abs", "band_rms_normalized"} <= set(df.columns)
    assert len(df) == 2  # two holes
