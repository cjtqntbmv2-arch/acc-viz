from __future__ import annotations

from pathlib import Path

import pytest

from tests.io.conftest import write_csv

ROWS = [(f, 1e-3, 2e-3, 3e-3) for f in (0.0, 1.0, 2.0, 3.0, 4.0)]


@pytest.fixture
def smoke_plate_folder(tmp_path) -> Path:
    write_csv(tmp_path / "x1-y1.csv", ROWS)
    write_csv(tmp_path / "x1-y2.csv", ROWS)
    write_csv(tmp_path / "x2-y1.csv", ROWS)
    write_csv(tmp_path / "Referenz.csv", ROWS)
    return tmp_path
