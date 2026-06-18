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


def test_load_plate_reports_progress_once_per_file(tmp_path):
    _populate_plate(tmp_path)  # 3 hole files + Referenz.csv = 4 files
    calls: list[tuple[int, int, str]] = []
    load_plate(tmp_path, progress=lambda done, total, name: calls.append((done, total, name)))
    dones = [c[0] for c in calls]
    assert dones == [1, 2, 3, 4]
    assert all(c[1] == 4 for c in calls)
    assert all(c[2].lower().endswith(".csv") for c in calls)


def test_load_plate_without_progress_is_unchanged(tmp_path):
    _populate_plate(tmp_path)
    result = load_plate(tmp_path)
    assert set(result.hole_data.keys()) == {(1, 1), (1, 2), (2, 1)}


def test_load_plate_cancel_aborts_before_reading_remaining(tmp_path):
    from src.io.schema import LoadCancelled

    _populate_plate(tmp_path)
    seen: list[str] = []

    def cb(done, total, name):
        seen.append(name)
        if done == 2:
            raise LoadCancelled

    with pytest.raises(LoadCancelled):
        load_plate(tmp_path, progress=cb)
    assert len(seen) == 2


def test_count_plate_files_matches_parsed_count_ignoring_strays(tmp_path):
    _populate_plate(tmp_path)                 # 4 parsable files
    (tmp_path / "notes.csv").write_text("irrelevant\n")   # stray, must be ignored
    from src.io.plate_loader import count_plate_files
    calls: list[int] = []
    load_plate(tmp_path, progress=lambda d, t, n: calls.append(d))
    assert count_plate_files(tmp_path) == 4
    assert len(calls) == 4
