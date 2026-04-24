from __future__ import annotations

import pytest
from pathlib import Path

from src.io.schema import (
    REQUIRED_COLUMNS,
    AccVizError,
    InvalidPlateFolderError,
    CsvReadError,
    CsvSchemaError,
    CsvContentError,
)


def test_required_columns_set():
    assert REQUIRED_COLUMNS == {"Frequenz_Hz", "PSD_X_g2Hz", "PSD_Y_g2Hz", "PSD_Z_g2Hz"}


def test_exceptions_inherit_base():
    for exc_cls in (InvalidPlateFolderError, CsvReadError, CsvSchemaError, CsvContentError):
        assert issubclass(exc_cls, AccVizError)


def test_invalid_folder_carries_context():
    exc = InvalidPlateFolderError(path=Path("/tmp/x"), reason="not_exists")
    assert exc.path == Path("/tmp/x")
    assert exc.reason == "not_exists"
    assert "/tmp/x" in str(exc)


def test_csv_schema_error_lists_missing():
    exc = CsvSchemaError(path=Path("/a.csv"), missing={"PSD_X_g2Hz"})
    assert exc.missing == {"PSD_X_g2Hz"}
    assert "PSD_X_g2Hz" in str(exc)


def test_csv_read_error_carries_path():
    exc = CsvReadError(path=Path("/a.csv"), reason="encoding")
    assert exc.path == Path("/a.csv")
    assert exc.reason == "encoding"
