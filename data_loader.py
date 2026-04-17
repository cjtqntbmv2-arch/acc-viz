import re
import pandas as pd
from pathlib import Path

_HEADER_LINES = 11
_HOLE_PATTERN = re.compile(r"^x(\d+)-y(\d+)\.csv$")


def load_plate(folder: str) -> tuple[dict[tuple[int, int], pd.DataFrame], pd.DataFrame | None]:
    folder_path = Path(folder)
    hole_data: dict[tuple[int, int], pd.DataFrame] = {}

    for csv_file in sorted(folder_path.glob("*.csv")):
        m = _HOLE_PATTERN.match(csv_file.name)
        if m:
            x, y = int(m.group(1)), int(m.group(2))
            hole_data[(x, y)] = _read_csv(csv_file)

    ref_path = folder_path / "Referenz.csv"
    ref_df = _read_csv(ref_path) if ref_path.exists() else None

    return hole_data, ref_df


def _read_csv(path: Path) -> pd.DataFrame:
    return pd.read_csv(path, skiprows=_HEADER_LINES)
