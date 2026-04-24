from __future__ import annotations

import pytest
from pathlib import Path

from src.io.plate_loader import load_plate, LoadResult
from src.io.schema import InvalidPlateFolderError, CsvSchemaError
from tests.io.conftest import write_csv

ROWS = [(0.0, 1e-3, 2e-3, 3e-3), (1.0, 1e-3, 2e-3, 3e-3), (2.0, 1e-3, 2e-3, 3e-3)]


def _populate_plate(folder: Path, *, with_ref: bool = True):
    write_csv(folder / "x1-y1.csv", ROWS)
    write_csv(folder / "x1-y2.csv", ROWS)
    write_csv(folder / "x2-y1.csv", ROWS)
    if with_ref:
        write_csv(folder / "Referenz.csv", ROWS)


def test_loads_hole_files_and_reference(tmp_path):
    _populate_plate(tmp_path)
    result = load_plate(tmp_path)
    assert isinstance(result, LoadResult)
    assert set(result.hole_data.keys()) == {(1, 1), (1, 2), (2, 1)}
    assert result.ref_df is not None
    assert result.warnings == []


def test_missing_reference_produces_warning_not_error(tmp_path):
    _populate_plate(tmp_path, with_ref=False)
    result = load_plate(tmp_path)
    assert result.ref_df is None
    assert any("Referenz" in w for w in result.warnings)


def test_nonexistent_folder_raises(tmp_path):
    with pytest.raises(InvalidPlateFolderError) as ei:
        load_plate(tmp_path / "does_not_exist")
    assert ei.value.reason == "not_exists"


def test_empty_folder_raises(tmp_path):
    with pytest.raises(InvalidPlateFolderError) as ei:
        load_plate(tmp_path)
    assert ei.value.reason == "empty"


def test_non_matching_filenames_ignored(tmp_path):
    _populate_plate(tmp_path)
    (tmp_path / "notes.csv").write_text("irrelevant\n")
    (tmp_path / "x1-y1.bak").write_text("irrelevant\n")
    result = load_plate(tmp_path)
    assert set(result.hole_data.keys()) == {(1, 1), (1, 2), (2, 1)}


def test_strict_mode_schema_error_on_single_bad_file(tmp_path):
    write_csv(tmp_path / "x1-y1.csv", ROWS)
    # Broken file: missing columns.
    (tmp_path / "x1-y2.csv").write_text("# junk\nFrequenz_Hz,PSD_X_g2Hz\n0.0,1e-3\n1.0,1e-3\n")
    with pytest.raises(CsvSchemaError):
        load_plate(tmp_path)


def test_case_insensitive_reference_lookup(tmp_path):
    _populate_plate(tmp_path, with_ref=False)
    write_csv(tmp_path / "REFERENZ.CSV", ROWS)
    result = load_plate(tmp_path)
    assert result.ref_df is not None
