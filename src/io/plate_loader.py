from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

import pandas as pd

from src.io.csv_reader import read_measurement_csv
from src.io.schema import InvalidPlateFolderError

_HOLE_PATTERN = re.compile(r"^x(\d+)-y(\d+)\.csv$", re.IGNORECASE)
_REFERENCE_NAME = "referenz.csv"


@dataclass
class LoadResult:
    hole_data: dict[tuple[int, int], pd.DataFrame]
    ref_df: pd.DataFrame | None
    warnings: list[str] = field(default_factory=list)


def load_plate(folder: Path | str) -> LoadResult:
    folder_path = Path(folder)

    if not folder_path.exists():
        raise InvalidPlateFolderError(path=folder_path, reason="not_exists")
    if not folder_path.is_dir():
        raise InvalidPlateFolderError(path=folder_path, reason="not_a_dir")

    hole_data: dict[tuple[int, int], pd.DataFrame] = {}
    ref_df: pd.DataFrame | None = None
    warnings: list[str] = []

    for entry in sorted(folder_path.iterdir()):
        if not entry.is_file():
            continue
        name_lower = entry.name.lower()

        if name_lower == _REFERENCE_NAME:
            ref_df = read_measurement_csv(entry)
            continue

        m = _HOLE_PATTERN.match(entry.name)
        if m:
            x, y = int(m.group(1)), int(m.group(2))
            hole_data[(x, y)] = read_measurement_csv(entry)

    if not hole_data:
        raise InvalidPlateFolderError(path=folder_path, reason="empty")

    if ref_df is None:
        warnings.append("Referenz.csv nicht gefunden — Normalisierung deaktiviert.")

    return LoadResult(hole_data=hole_data, ref_df=ref_df, warnings=warnings)
