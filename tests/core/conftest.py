from __future__ import annotations

"""Helpers for building plate folders on disk for pipeline tests."""

from pathlib import Path

import pandas as pd

_HEADER = "Frequenz_Hz,PSD_X_g2Hz,PSD_Y_g2Hz,PSD_Z_g2Hz\n"


def make_df(freqs: list[float], val: float) -> pd.DataFrame:
    return pd.DataFrame({
        "Frequenz_Hz": freqs,
        "PSD_X_g2Hz": [val] * len(freqs),
        "PSD_Y_g2Hz": [val] * len(freqs),
        "PSD_Z_g2Hz": [val] * len(freqs),
    })


def _write_csv(path: Path, freqs: list[float], val: float) -> None:
    lines = [_HEADER]
    for f in freqs:
        lines.append(f"{f},{val},{val},{val}\n")
    path.write_text("".join(lines), encoding="utf-8")


def make_plate_folder(
    root: Path,
    holes: dict[tuple[int, int], float],
    *,
    freqs: list[float] | None = None,
    ref_val: float | None = None,
) -> Path:
    """Create a plate folder with one ``x{N}-y{M}.csv`` per hole and optional Referenz.csv."""
    freqs = freqs if freqs is not None else [0.0, 1.0, 2.0]
    root.mkdir(parents=True, exist_ok=True)
    for (x, y), val in holes.items():
        _write_csv(root / f"x{x}-y{y}.csv", freqs, val)
    if ref_val is not None:
        _write_csv(root / "Referenz.csv", freqs, ref_val)
    return root
