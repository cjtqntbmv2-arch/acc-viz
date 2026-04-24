from __future__ import annotations

import io
from pathlib import Path

import pandas as pd

from src.io.schema import (
    REQUIRED_COLUMNS,
    CsvContentError,
    CsvReadError,
    CsvSchemaError,
)

_ENCODINGS = ("utf-8-sig", "utf-8", "cp1252", "latin-1")
_CANDIDATE_SEPS = (";", ",", "\t")
_HEADER_SEARCH_LIMIT = 30
_HEADER_MARKER = "Frequenz_Hz"


def _decode(raw: bytes, path: Path) -> str:
    for enc in _ENCODINGS:
        try:
            return raw.decode(enc)
        except UnicodeDecodeError:
            continue
    raise CsvReadError(path=path, reason="encoding")


def _find_header_line(text_lines: list[str], path: Path) -> int:
    for i, line in enumerate(text_lines[:_HEADER_SEARCH_LIMIT]):
        if _HEADER_MARKER in line:
            return i
    # Fallback to historic default if file has enough lines
    if len(text_lines) > 11:
        return 11
    raise CsvReadError(path=path, reason="parse")


def _pick_separator(header_line: str) -> str:
    counts = {sep: header_line.count(sep) for sep in _CANDIDATE_SEPS}
    best = max(counts, key=lambda s: counts[s])
    if counts[best] == 0:
        return ","
    return best


def read_measurement_csv(path: Path) -> pd.DataFrame:
    """Read a measurement CSV with robust encoding/separator/decimal handling."""
    try:
        raw = Path(path).read_bytes()
    except OSError as e:
        raise CsvReadError(path=Path(path), reason="parse") from e

    text = _decode(raw, Path(path))
    lines = text.splitlines()
    if not lines:
        raise CsvReadError(path=Path(path), reason="parse")

    header_idx = _find_header_line(lines, Path(path))
    sep = _pick_separator(lines[header_idx])
    decimal = "," if sep == ";" else "."

    try:
        df = pd.read_csv(
            io.StringIO(text),
            skiprows=header_idx,
            sep=sep,
            decimal=decimal,
            engine="python",
        )
    except Exception as e:
        raise CsvReadError(path=Path(path), reason="parse") from e

    missing = REQUIRED_COLUMNS - set(df.columns)
    if missing:
        raise CsvSchemaError(path=Path(path), missing=missing)

    for col in REQUIRED_COLUMNS:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    df = df.dropna(subset=list(REQUIRED_COLUMNS)).reset_index(drop=True)

    if len(df) < 2:
        raise CsvContentError(path=Path(path), reason="too_few_rows")

    return pd.DataFrame(df[["Frequenz_Hz", "PSD_X_g2Hz", "PSD_Y_g2Hz", "PSD_Z_g2Hz"]])
