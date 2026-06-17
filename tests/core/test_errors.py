from __future__ import annotations

from pathlib import Path

from src.io.schema import (
    InvalidPlateFolderError,
    CsvReadError,
    CsvSchemaError,
    CsvContentError,
    AccVizError,
)
from src.core.errors import format_error


def test_format_invalid_folder_not_exists():
    path = Path("/x")
    exc = InvalidPlateFolderError(path=path, reason="not_exists")
    msg = format_error(exc, plate_label="Platte 1")
    assert "Pfad existiert nicht" in msg
    # Use platform-native string form so the test passes on Windows too
    # where Path separators are backslashes rather than forward slashes.
    assert str(path) in msg


def test_format_invalid_folder_empty():
    exc = InvalidPlateFolderError(path=Path("/x"), reason="empty")
    msg = format_error(exc, plate_label="Platte 1")
    assert "keine Dateien" in msg


def test_format_csv_read():
    path = Path("/a.csv")
    exc = CsvReadError(path=path, reason="encoding")
    msg = format_error(exc, plate_label="Platte 1")
    assert "Encoding" in msg or "gelesen werden" in msg
    assert str(path) in msg


def test_format_csv_schema_includes_missing():
    exc = CsvSchemaError(path=Path("/a.csv"), missing={"PSD_Y_g2Hz"})
    msg = format_error(exc, plate_label="Platte 1")
    assert "PSD_Y_g2Hz" in msg


def test_format_csv_content():
    exc = CsvContentError(path=Path("/a.csv"), reason="too_few_rows")
    msg = format_error(exc, plate_label="Platte 1")
    assert "Messwerte" in msg


def test_format_unknown_fallback():
    class Other(AccVizError):
        pass
    msg = format_error(Other("boom"), plate_label="Platte 1")
    assert "Platte 1" in msg
    assert "boom" in msg
