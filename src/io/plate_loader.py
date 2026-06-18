from __future__ import annotations

"""Load a plate folder of hole measurement CSVs plus an optional reference file."""

import re
from dataclasses import dataclass, field
from pathlib import Path

import pandas as pd

from src.io.csv_reader import read_measurement_csv
from src.io.schema import InvalidPlateFolderError, ProgressCallback

_HOLE_PATTERN = re.compile(r"^x(\d+)-y(\d+)\.csv$", re.IGNORECASE)
_REFERENCE_NAME = "referenz.csv"


@dataclass
class LoadResult:
    """Container for the parsed contents of a plate folder."""

    hole_data: dict[tuple[int, int], pd.DataFrame]
    ref_df: pd.DataFrame | None
    warnings: list[str] = field(default_factory=list)


def _is_plate_file(entry: Path) -> bool:
    """True for files load_plate parses: a hole file or the reference file."""
    if not entry.is_file():
        return False
    name_lower = entry.name.lower()
    return name_lower == _REFERENCE_NAME or bool(_HOLE_PATTERN.match(entry.name))


def count_plate_files(folder: Path | str) -> int:
    """Number of files :func:`load_plate` would parse; 0 for a missing folder."""
    folder_path = Path(folder)
    if not folder_path.is_dir():
        return 0
    return sum(1 for entry in folder_path.iterdir() if _is_plate_file(entry))


def load_plate(folder: Path | str, *, progress: ProgressCallback | None = None) -> LoadResult:
    """Load every ``x{N}-y{M}.csv`` hole file and the optional ``Referenz.csv``.

    File discovery is case-insensitive and limited to regular files directly
    inside ``folder``. Files that do not match the hole or reference naming
    conventions are ignored silently.

    Args:
        folder: Path to the plate folder.

    Returns:
        A :class:`LoadResult` with the parsed hole DataFrames, the reference
        DataFrame (or ``None`` when missing), and any non-fatal warnings.

    Raises:
        InvalidPlateFolderError: If ``folder`` does not exist, is not a
            directory, or contains no hole files.
    """
    folder_path = Path(folder)

    if not folder_path.exists():
        raise InvalidPlateFolderError(path=folder_path, reason="not_exists")
    if not folder_path.is_dir():
        raise InvalidPlateFolderError(path=folder_path, reason="not_a_dir")

    to_parse = [entry for entry in sorted(folder_path.iterdir()) if _is_plate_file(entry)]
    total = len(to_parse)

    hole_data: dict[tuple[int, int], pd.DataFrame] = {}
    ref_df: pd.DataFrame | None = None
    warnings: list[str] = []

    for i, entry in enumerate(to_parse, start=1):
        if progress is not None:
            progress(i, total, entry.name)
        if entry.name.lower() == _REFERENCE_NAME:
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
