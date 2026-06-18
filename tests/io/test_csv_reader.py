from __future__ import annotations

import math
import pytest
from pathlib import Path

from src.io.csv_reader import read_measurement_csv
from src.io.schema import CsvReadError, CsvSchemaError, CsvContentError
from tests.io.conftest import write_csv


ROWS = [(0.0, 1e-3, 2e-3, 3e-3), (1.0, 1e-3, 2e-3, 3e-3), (2.0, 1e-3, 2e-3, 3e-3)]


def test_reads_utf8_comma(tmp_path):
    p = tmp_path / "x1-y1.csv"
    write_csv(p, ROWS)
    df = read_measurement_csv(p)
    assert list(df.columns) == ["Frequenz_Hz", "PSD_X_g2Hz", "PSD_Y_g2Hz", "PSD_Z_g2Hz"]
    assert len(df) == 3


def test_reads_utf8_bom(tmp_path):
    p = tmp_path / "x1-y1.csv"
    write_csv(p, ROWS, bom=True)
    df = read_measurement_csv(p)
    assert math.isclose(df["PSD_X_g2Hz"].iloc[0], 1e-3)


def test_reads_cp1252_semicolon_decimal_comma(tmp_path):
    p = tmp_path / "x1-y1.csv"
    write_csv(p, ROWS, sep=";", decimal=",", encoding="cp1252")
    df = read_measurement_csv(p)
    assert math.isclose(df["PSD_X_g2Hz"].iloc[0], 1e-3)


def test_reads_latin1(tmp_path):
    p = tmp_path / "x1-y1.csv"
    write_csv(p, ROWS, encoding="latin-1")
    df = read_measurement_csv(p)
    assert len(df) == 3


def test_finds_header_when_extra_comment_lines(tmp_path):
    p = tmp_path / "x1-y1.csv"
    write_csv(p, ROWS, header_extra_lines=3)  # Header now on line 15 instead of 12
    df = read_measurement_csv(p)
    assert len(df) == 3


def test_missing_required_column_raises_schema_error(tmp_path):
    p = tmp_path / "x1-y1.csv"
    lines = [
        "# comment",
        "Frequenz_Hz,PSD_X_g2Hz",  # PSD_Y, PSD_Z missing
        "0.0,1e-3",
        "1.0,1e-3",
    ]
    p.write_text("\n".join(lines) + "\n")
    with pytest.raises(CsvSchemaError) as exc_info:
        read_measurement_csv(p)
    assert "PSD_Y_g2Hz" in exc_info.value.missing
    assert "PSD_Z_g2Hz" in exc_info.value.missing


def test_malformed_file_raises_read_error(tmp_path):
    p = tmp_path / "x1-y1.csv"
    p.write_bytes(b"\x00\x01\x02\x03\xff\xfe")
    with pytest.raises((CsvReadError, CsvSchemaError)):
        read_measurement_csv(p)


def test_too_few_rows_raises_content_error(tmp_path):
    p = tmp_path / "x1-y1.csv"
    write_csv(p, [(0.0, 1e-3, 2e-3, 3e-3)])  # only one data row
    with pytest.raises(CsvContentError):
        read_measurement_csv(p)


def test_unknown_separator_raises_read_error(tmp_path):
    p = tmp_path / "x1-y1.csv"
    lines = ["# comment"] * 10 + [
        "Frequenz_Hz|PSD_X_g2Hz|PSD_Y_g2Hz|PSD_Z_g2Hz",
        "0.0|1e-3|2e-3|3e-3",
        "1.0|1e-3|2e-3|3e-3",
    ]
    p.write_text("\n".join(lines) + "\n")
    with pytest.raises(CsvReadError) as ei:
        read_measurement_csv(p)
    assert ei.value.reason == "separator"


def test_binary_file_raises_encoding_error(tmp_path):
    p = tmp_path / "x1-y1.csv"
    p.write_bytes(b"header\x00binary\x00data\x00\x00")
    with pytest.raises(CsvReadError) as ei:
        read_measurement_csv(p)
    assert ei.value.reason == "encoding"


def test_no_header_marker_raises_parse_error(tmp_path):
    p = tmp_path / "x1-y1.csv"
    p.write_text("\n".join(f"# junk line {i}" for i in range(35)) + "\n")
    with pytest.raises(CsvReadError) as ei:
        read_measurement_csv(p)
    assert ei.value.reason == "parse"


def test_parses_many_rows_semicolon_decimal_comma(tmp_path):
    rows = [(float(i), 1e-3, 2e-3, 3e-3) for i in range(2000)]
    p = tmp_path / "x1-y1.csv"
    write_csv(p, rows, sep=";", decimal=",", encoding="cp1252")
    df = read_measurement_csv(p)
    assert len(df) == 2000
    assert list(df.columns) == ["Frequenz_Hz", "PSD_X_g2Hz", "PSD_Y_g2Hz", "PSD_Z_g2Hz"]
    assert math.isclose(df["PSD_Z_g2Hz"].iloc[-1], 3e-3)
