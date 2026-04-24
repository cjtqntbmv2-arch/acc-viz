# Robustness & Deployment Refactor Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Restructure `acc_visualisation` into layered modules, harden CSV IO, enforce strict typed error handling, clean up the Streamlit UI, and make the app PyInstaller-bundleable for Windows + macOS.

**Architecture:** New `src/` package with four layers — `analysis/` (pure numerics), `io/` (CSV + validation), `ui/` (Streamlit), `platform_utils/` (OS-specific). `app.py` becomes a thin composition root. `packaging/` holds PyInstaller entry and build script. Tests per layer.

**Tech Stack:** Python 3.10+, Streamlit ≥ 1.35, pandas, numpy, scipy, plotly, PyInstaller, pytest, GitHub Actions.

**Spec:** [docs/superpowers/specs/2026-04-24-robustness-refactor-design.md](../specs/2026-04-24-robustness-refactor-design.md)

---

## Conventions

- Every source file starts with `from __future__ import annotations`.
- `pathlib.Path` everywhere for filesystem paths; no string concatenation.
- Paths with `abs_path = Path(user_input.strip().strip('"').strip("'"))` when entering from UI.
- All German UI strings live in `src/ui/strings.py`.
- Test file layout mirrors source: `tests/<layer>/test_<module>.py`.
- Commit after each task's tests pass. Commit message prefix: `refactor:`, `feat:`, `test:`, `fix:` as appropriate.

## File Structure Being Built

```
src/
├── __init__.py
├── analysis/
│   ├── __init__.py
│   ├── rms.py
│   ├── grid.py
│   └── interpolation.py
├── io/
│   ├── __init__.py
│   ├── schema.py
│   ├── csv_reader.py
│   └── plate_loader.py
├── ui/
│   ├── __init__.py
│   ├── strings.py
│   ├── errors.py
│   ├── sidebar.py
│   ├── heatmap.py
│   ├── spectrum.py
│   └── export.py
└── platform_utils/
    ├── __init__.py
    ├── subprocess_utils.py
    └── folder_picker.py

packaging/
├── entry.py
├── acc_viz.spec
└── build.py

tests/
├── analysis/
│   ├── __init__.py
│   ├── test_rms.py
│   ├── test_grid.py
│   └── test_interpolation.py
├── io/
│   ├── __init__.py
│   ├── conftest.py
│   ├── fixtures/  (sample CSVs)
│   ├── test_csv_reader.py
│   └── test_plate_loader.py
├── platform_utils/
│   ├── __init__.py
│   └── test_folder_picker.py
└── ui/
    ├── __init__.py
    └── test_smoke.py
```

Files deleted at the end: `processing.py`, `data_loader.py`, old `tests/test_processing.py`, `tests/test_data_loader.py`.

`app.py` is rewritten in the final phase.

---

## Task 1: Set up `src/` package skeleton

**Files:**
- Create: `src/__init__.py` (empty)
- Create: `src/analysis/__init__.py` (empty)
- Create: `src/io/__init__.py` (empty)
- Create: `src/ui/__init__.py` (empty)
- Create: `src/platform_utils/__init__.py` (empty)
- Create: `pyproject.toml` (for `pytest` rootdir and Python version)

- [ ] **Step 1: Create package directories and empty `__init__.py` files**

```bash
mkdir -p src/analysis src/io src/ui src/platform_utils
touch src/__init__.py src/analysis/__init__.py src/io/__init__.py src/ui/__init__.py src/platform_utils/__init__.py
```

- [ ] **Step 2: Create `pyproject.toml`**

```toml
[build-system]
requires = ["setuptools>=61.0"]
build-backend = "setuptools.build_meta"

[project]
name = "acc-visualisation"
version = "0.1.0"
requires-python = ">=3.10"

[tool.pytest.ini_options]
testpaths = ["tests"]
pythonpath = ["."]

[tool.setuptools.packages.find]
where = ["."]
include = ["src*"]
```

- [ ] **Step 3: Verify existing tests still pass**

Run: `python3 -m pytest -q`
Expected: PASS (existing tests under `tests/test_processing.py` and `tests/test_data_loader.py`).

- [ ] **Step 4: Commit**

```bash
git add src/ pyproject.toml
git commit -m "refactor: add src/ package skeleton"
```

---

## Task 2: Extract `compute_band_rms` to `src/analysis/rms.py` (TDD)

**Files:**
- Create: `src/analysis/rms.py`
- Create: `tests/analysis/__init__.py`
- Create: `tests/analysis/test_rms.py`

- [ ] **Step 1: Write failing test file**

`tests/analysis/test_rms.py`:

```python
from __future__ import annotations

import math
import pandas as pd
from src.analysis.rms import compute_band_rms


def _df(freqs, psd_x, psd_y=0.0, psd_z=0.0):
    return pd.DataFrame({
        "Frequenz_Hz": freqs,
        "PSD_X_g2Hz": [psd_x] * len(freqs) if not isinstance(psd_x, list) else psd_x,
        "PSD_Y_g2Hz": [psd_y] * len(freqs) if not isinstance(psd_y, list) else psd_y,
        "PSD_Z_g2Hz": [psd_z] * len(freqs) if not isinstance(psd_z, list) else psd_z,
    })


def test_compute_band_rms_full_range():
    df = _df([0.0, 1.0, 2.0, 3.0, 4.0], 1e-3)
    result = compute_band_rms(df, f_min=0.0, f_max=4.0, axis="X")
    assert math.isclose(result, math.sqrt(4e-3), rel_tol=1e-6)


def test_compute_band_rms_partial_range():
    df = _df([0.0, 1.0, 2.0, 3.0, 4.0], 1e-3)
    result = compute_band_rms(df, f_min=1.0, f_max=2.0, axis="X")
    assert math.isclose(result, math.sqrt(1e-3), rel_tol=1e-6)


def test_compute_band_rms_axis_selection():
    df = _df([0.0, 1.0, 2.0], 1e-3, 4e-3, 9e-3)
    assert math.isclose(compute_band_rms(df, 0.0, 2.0, "Y"), math.sqrt(2 * 4e-3), rel_tol=1e-6)
    assert math.isclose(compute_band_rms(df, 0.0, 2.0, "Z"), math.sqrt(2 * 9e-3), rel_tol=1e-6)


def test_compute_band_rms_band_outside_data_is_nan():
    df = _df([0.0, 1.0, 2.0], 1e-3)
    assert math.isnan(compute_band_rms(df, 10.0, 20.0, "X"))


def test_compute_band_rms_fmin_equals_fmax_is_nan():
    df = _df([0.0, 1.0, 2.0], 1e-3)
    assert math.isnan(compute_band_rms(df, 1.0, 1.0, "X"))


def test_compute_band_rms_single_point_in_band_is_nan():
    df = _df([0.0, 5.0, 10.0], 1e-3)
    assert math.isnan(compute_band_rms(df, 4.0, 6.0, "X"))


def test_compute_band_rms_all_nan_in_band_is_nan():
    df = pd.DataFrame({
        "Frequenz_Hz": [0.0, 1.0, 2.0],
        "PSD_X_g2Hz": [float("nan")] * 3,
        "PSD_Y_g2Hz": [0.0] * 3,
        "PSD_Z_g2Hz": [0.0] * 3,
    })
    assert math.isnan(compute_band_rms(df, 0.0, 2.0, "X"))
```

Note the fix from the old test suite: the old `test_compute_band_rms_full_range` asserted `sqrt(5e-3)` for a trapezoidal integral, but `np.trapezoid` of a constant `1e-3` over `[0, 4]` = `4e-3`. The old test was wrong; the new one is correct.

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/analysis/test_rms.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'src.analysis.rms'`.

- [ ] **Step 3: Implement `src/analysis/rms.py`**

```python
from __future__ import annotations

import math
import numpy as np
import pandas as pd


def compute_band_rms(df: pd.DataFrame, f_min: float, f_max: float, axis: str) -> float:
    """Compute sqrt(integral of PSD over [f_min, f_max]) for the given axis.
    Returns NaN if fewer than 2 valid data points fall inside the band.
    """
    if f_min >= f_max:
        return math.nan
    col = f"PSD_{axis}_g2Hz"
    mask = (df["Frequenz_Hz"] >= f_min) & (df["Frequenz_Hz"] <= f_max)
    sub = df.loc[mask, ["Frequenz_Hz", col]].sort_values("Frequenz_Hz").dropna()
    if len(sub) < 2:
        return math.nan
    return float(np.sqrt(np.trapezoid(sub[col].to_numpy(), sub["Frequenz_Hz"].to_numpy())))
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/analysis/test_rms.py -v`
Expected: PASS (7 tests).

- [ ] **Step 5: Commit**

```bash
git add src/analysis/rms.py tests/analysis/__init__.py tests/analysis/test_rms.py
git commit -m "refactor: extract compute_band_rms to src/analysis/rms.py"
```

---

## Task 3: Extract `build_grid` to `src/analysis/grid.py` (TDD)

**Files:**
- Create: `src/analysis/grid.py`
- Create: `tests/analysis/test_grid.py`

- [ ] **Step 1: Write failing test file**

`tests/analysis/test_grid.py`:

```python
from __future__ import annotations

import math
import pandas as pd
from src.analysis.grid import build_grid


def _df(freqs, val):
    return pd.DataFrame({
        "Frequenz_Hz": freqs,
        "PSD_X_g2Hz": [val] * len(freqs),
        "PSD_Y_g2Hz": [val] * len(freqs),
        "PSD_Z_g2Hz": [val] * len(freqs),
    })


def test_build_grid_shape_from_max_xy():
    holes = {
        (1, 1): _df([0.0, 1.0, 2.0], 1e-3),
        (1, 2): _df([0.0, 1.0, 2.0], 1e-3),
        (2, 1): _df([0.0, 1.0, 2.0], 1e-3),
    }
    g = build_grid(holes, None, 0.0, 2.0, "X", normalize=False)
    assert g.shape == (2, 2)


def test_build_grid_missing_hole_is_nan():
    holes = {(1, 1): _df([0.0, 1.0, 2.0], 1e-3), (2, 2): _df([0.0, 1.0, 2.0], 1e-3)}
    g = build_grid(holes, None, 0.0, 2.0, "X", normalize=False)
    assert math.isnan(g[0, 1])
    assert math.isnan(g[1, 0])


def test_build_grid_absolute_value():
    holes = {(1, 1): _df([0.0, 1.0, 2.0], 1e-3)}
    g = build_grid(holes, None, 0.0, 2.0, "X", normalize=False)
    assert math.isclose(g[0, 0], math.sqrt(2e-3), rel_tol=1e-6)


def test_build_grid_normalized_against_reference():
    ref = _df([0.0, 1.0, 2.0], 1e-3)
    holes = {(1, 1): _df([0.0, 1.0, 2.0], 4e-3)}
    g = build_grid(holes, ref, 0.0, 2.0, "X", normalize=True)
    assert math.isclose(g[0, 0], 2.0, rel_tol=1e-6)


def test_build_grid_normalize_without_ref_uses_absolute():
    holes = {(1, 1): _df([0.0, 1.0, 2.0], 4e-3)}
    g = build_grid(holes, None, 0.0, 2.0, "X", normalize=True)
    assert math.isclose(g[0, 0], math.sqrt(2 * 4e-3), rel_tol=1e-6)


def test_build_grid_empty_returns_nan_1x1():
    g = build_grid({}, None, 0.0, 2.0, "X", normalize=False)
    assert g.shape == (1, 1)
    assert math.isnan(g[0, 0])


def test_build_grid_ref_rms_zero_falls_back_to_absolute():
    ref = _df([0.0, 1.0, 2.0], 0.0)
    holes = {(1, 1): _df([0.0, 1.0, 2.0], 4e-3)}
    g = build_grid(holes, ref, 0.0, 2.0, "X", normalize=True)
    assert math.isclose(g[0, 0], math.sqrt(2 * 4e-3), rel_tol=1e-6)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/analysis/test_grid.py -v`
Expected: FAIL — module missing.

- [ ] **Step 3: Implement `src/analysis/grid.py`**

```python
from __future__ import annotations

import numpy as np
import pandas as pd

from src.analysis.rms import compute_band_rms


def build_grid(
    hole_data: dict[tuple[int, int], pd.DataFrame],
    ref_df: pd.DataFrame | None,
    f_min: float,
    f_max: float,
    axis: str,
    normalize: bool,
) -> np.ndarray:
    """Build an (max_x, max_y) grid of band-RMS values, NaN where no data."""
    if not hole_data:
        return np.full((1, 1), np.nan)

    max_x = max(x for x, _ in hole_data)
    max_y = max(y for _, y in hole_data)
    grid = np.full((max_x, max_y), np.nan)

    ref_rms = compute_band_rms(ref_df, f_min, f_max, axis) if ref_df is not None else None
    use_norm = normalize and ref_rms is not None and np.isfinite(ref_rms) and ref_rms > 0

    for (x, y), df in hole_data.items():
        rms = compute_band_rms(df, f_min, f_max, axis)
        grid[x - 1, y - 1] = rms / ref_rms if use_norm else rms

    return grid
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python3 -m pytest tests/analysis/test_grid.py -v`
Expected: PASS (7 tests).

- [ ] **Step 5: Commit**

```bash
git add src/analysis/grid.py tests/analysis/test_grid.py
git commit -m "refactor: extract build_grid to src/analysis/grid.py"
```

---

## Task 4: Extract `interpolate_grid` to `src/analysis/interpolation.py` (TDD)

**Files:**
- Create: `src/analysis/interpolation.py`
- Create: `tests/analysis/test_interpolation.py`

- [ ] **Step 1: Write failing test file**

`tests/analysis/test_interpolation.py`:

```python
from __future__ import annotations

import numpy as np
from src.analysis.interpolation import interpolate_grid


def test_fills_interior_linearly():
    grid = np.array([
        [1.0, np.nan, 3.0],
        [np.nan, np.nan, np.nan],
        [1.0, np.nan, 3.0],
    ])
    result = interpolate_grid(grid)
    assert not np.isnan(result[1, 1])
    assert np.isclose(result[1, 1], 2.0, atol=0.1)


def test_preserves_known_values():
    grid = np.array([
        [1.0, np.nan, 3.0],
        [np.nan, np.nan, np.nan],
        [1.0, np.nan, 3.0],
    ])
    result = interpolate_grid(grid)
    assert np.isclose(result[0, 0], 1.0)
    assert np.isclose(result[0, 2], 3.0)


def test_outside_convex_hull_filled_by_nearest():
    grid = np.full((5, 5), np.nan)
    grid[2, 1] = 1.0
    grid[2, 3] = 2.0
    grid[3, 2] = 3.0
    result = interpolate_grid(grid)
    # No NaNs should remain — nearest fills outside the hull.
    assert not np.isnan(result).any()


def test_too_few_points_returns_copy():
    grid = np.full((3, 3), np.nan)
    grid[1, 1] = 5.0
    result = interpolate_grid(grid)
    assert np.isclose(result[1, 1], 5.0)
    assert np.isnan(result[0, 0])


def test_no_nan_unchanged():
    grid = np.array([[1.0, 2.0], [3.0, 4.0]])
    result = interpolate_grid(grid)
    assert np.allclose(result, grid)


def test_reference_value_used_at_center():
    grid = np.full((3, 3), np.nan)
    grid[0, 0] = 1.0
    grid[0, 2] = 1.0
    grid[2, 0] = 1.0
    grid[2, 2] = 1.0
    result = interpolate_grid(grid, ref_value=5.0)
    # Center should be pulled toward the reference value.
    assert result[1, 1] > 1.0
```

Note: the old test asserted corners remain NaN after linear interpolation; the new behaviour (spec) is to fill NaNs via nearest. That test is replaced above.

- [ ] **Step 2: Run to verify failure**

Run: `python3 -m pytest tests/analysis/test_interpolation.py -v`
Expected: FAIL — module missing.

- [ ] **Step 3: Implement `src/analysis/interpolation.py`**

```python
from __future__ import annotations

import numpy as np
from scipy.interpolate import griddata


def interpolate_grid(grid: np.ndarray, ref_value: float | None = None) -> np.ndarray:
    """Linearly interpolate NaNs; fill any remaining NaNs via nearest-neighbour.
    If ref_value is provided, it is injected at the geometric center."""
    known_mask = ~np.isnan(grid)
    nrows, ncols = grid.shape
    rows, cols = np.mgrid[0:nrows, 0:ncols]

    pts_list = [np.column_stack([rows[known_mask], cols[known_mask]])]
    vals_list = [grid[known_mask]]
    if ref_value is not None:
        pts_list.append(np.array([[(nrows - 1) / 2, (ncols - 1) / 2]]))
        vals_list.append(np.array([ref_value]))

    points = np.vstack(pts_list)
    values = np.concatenate(vals_list)

    if len(points) < 3:
        return grid.copy()

    linear = griddata(points, values, (rows, cols), method="linear")
    nan_mask = np.isnan(linear)
    if nan_mask.any():
        nearest = griddata(points, values, (rows, cols), method="nearest")
        linear[nan_mask] = nearest[nan_mask]
    return linear
```

- [ ] **Step 4: Run to verify pass**

Run: `python3 -m pytest tests/analysis/test_interpolation.py -v`
Expected: PASS (6 tests).

- [ ] **Step 5: Commit**

```bash
git add src/analysis/interpolation.py tests/analysis/test_interpolation.py
git commit -m "refactor: extract interpolate_grid to src/analysis/interpolation.py"
```

---

## Task 5: Define exception hierarchy in `src/io/schema.py` (TDD)

**Files:**
- Create: `src/io/schema.py`
- Create: `tests/io/__init__.py`
- Create: `tests/io/test_schema.py`

- [ ] **Step 1: Write failing test**

`tests/io/test_schema.py`:

```python
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
```

- [ ] **Step 2: Run to verify failure**

Run: `python3 -m pytest tests/io/test_schema.py -v`
Expected: FAIL — module missing.

- [ ] **Step 3: Implement `src/io/schema.py`**

```python
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

REQUIRED_COLUMNS: set[str] = {"Frequenz_Hz", "PSD_X_g2Hz", "PSD_Y_g2Hz", "PSD_Z_g2Hz"}


class AccVizError(Exception):
    """Base class for all acc_visualisation domain errors."""


@dataclass
class InvalidPlateFolderError(AccVizError):
    path: Path
    reason: str  # "not_exists" | "not_a_dir" | "empty"

    def __str__(self) -> str:
        return f"Invalid plate folder ({self.reason}): {self.path}"


@dataclass
class CsvReadError(AccVizError):
    path: Path
    reason: str  # "encoding" | "separator" | "parse"

    def __str__(self) -> str:
        return f"Could not read CSV ({self.reason}): {self.path}"


@dataclass
class CsvSchemaError(AccVizError):
    path: Path
    missing: set[str] = field(default_factory=set)

    def __str__(self) -> str:
        miss = ", ".join(sorted(self.missing))
        return f"CSV schema error in {self.path}: missing columns {{{miss}}}"


@dataclass
class CsvContentError(AccVizError):
    path: Path
    reason: str  # "too_few_rows" | "all_nan"

    def __str__(self) -> str:
        return f"CSV content error ({self.reason}): {self.path}"
```

Note: `@dataclass` on `Exception` subclasses requires the dataclass to declare its own `__init__`; that works out of the box.

- [ ] **Step 4: Run to verify pass**

Run: `python3 -m pytest tests/io/test_schema.py -v`
Expected: PASS (5 tests).

- [ ] **Step 5: Commit**

```bash
git add src/io/schema.py tests/io/__init__.py tests/io/test_schema.py
git commit -m "feat: add typed exception hierarchy in src/io/schema.py"
```

---

## Task 6: CSV reader in `src/io/csv_reader.py` (TDD)

**Files:**
- Create: `src/io/csv_reader.py`
- Create: `tests/io/conftest.py`
- Create: `tests/io/test_csv_reader.py`

- [ ] **Step 1: Write fixtures helper**

`tests/io/conftest.py`:

```python
from __future__ import annotations

from pathlib import Path

CSV_HEADER_LINES = [
    "# Quelle: PicoScope 4000a (Live)",
    "# Spannungsbereich: ±5 V",
    "# Kopplung: AC",
    "# Abtastrate: 50000.00 Hz",
    "# Samples/Block: 131072",
    "# Fensterfunktion: Hanning (ENBW = 1.50)",
    "# Frequenzauflösung: 1.0 Hz",
    "# Mittelung aus 20 Messungen (Leistungsdomäne)",
    "# Empfindlichkeit X/Y/Z: 10.07/10.08/10.78 mV/g",
    "# gRMS-Bereich: 0–25000 Hz",
    "# averaging_method: power",
]


def write_csv(
    path: Path,
    rows: list[tuple[float, float, float, float]],
    *,
    sep: str = ",",
    decimal: str = ".",
    encoding: str = "utf-8",
    header_extra_lines: int = 0,
    bom: bool = False,
) -> None:
    header = "Frequenz_Hz" + sep + sep.join(["PSD_X_g2Hz", "PSD_Y_g2Hz", "PSD_Z_g2Hz"])

    def fmt(v: float) -> str:
        s = repr(v)
        return s.replace(".", decimal) if decimal != "." else s

    data_lines = [sep.join(fmt(v) for v in row) for row in rows]

    lines = list(CSV_HEADER_LINES)
    for _ in range(header_extra_lines):
        lines.append("# extra comment")
    lines.append(header)
    lines.extend(data_lines)
    text = "\n".join(lines) + "\n"

    if bom:
        data_bytes = "\ufeff".encode(encoding) + text.encode(encoding)
    else:
        data_bytes = text.encode(encoding)
    path.write_bytes(data_bytes)
```

- [ ] **Step 2: Write failing tests**

`tests/io/test_csv_reader.py`:

```python
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
```

- [ ] **Step 3: Run to verify failure**

Run: `python3 -m pytest tests/io/test_csv_reader.py -v`
Expected: FAIL — module missing.

- [ ] **Step 4: Implement `src/io/csv_reader.py`**

```python
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


def _find_header_line(text_lines: list[str]) -> int:
    for i, line in enumerate(text_lines[:_HEADER_SEARCH_LIMIT]):
        if _HEADER_MARKER in line:
            return i
    # Fallback to historic default
    return 11


def _pick_separator(header_line: str) -> str:
    counts = {sep: header_line.count(sep) for sep in _CANDIDATE_SEPS}
    best = max(counts, key=counts.get)
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

    header_idx = _find_header_line(lines)
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

    return df[["Frequenz_Hz", "PSD_X_g2Hz", "PSD_Y_g2Hz", "PSD_Z_g2Hz"]]
```

- [ ] **Step 5: Run to verify pass**

Run: `python3 -m pytest tests/io/test_csv_reader.py -v`
Expected: PASS (8 tests).

- [ ] **Step 6: Commit**

```bash
git add src/io/csv_reader.py tests/io/conftest.py tests/io/test_csv_reader.py
git commit -m "feat: add robust CSV reader with encoding/separator detection"
```

---

## Task 7: Plate loader in `src/io/plate_loader.py` (TDD)

**Files:**
- Create: `src/io/plate_loader.py`
- Create: `tests/io/test_plate_loader.py`

- [ ] **Step 1: Write failing tests**

`tests/io/test_plate_loader.py`:

```python
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
```

- [ ] **Step 2: Run to verify failure**

Run: `python3 -m pytest tests/io/test_plate_loader.py -v`
Expected: FAIL — module missing.

- [ ] **Step 3: Implement `src/io/plate_loader.py`**

```python
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
```

- [ ] **Step 4: Run to verify pass**

Run: `python3 -m pytest tests/io/test_plate_loader.py -v`
Expected: PASS (7 tests).

- [ ] **Step 5: Commit**

```bash
git add src/io/plate_loader.py tests/io/test_plate_loader.py
git commit -m "feat: add strict plate loader with LoadResult"
```

---

## Task 8: Full analysis+io test suite green, remove old modules

**Files:**
- Delete: `processing.py`
- Delete: `data_loader.py`
- Delete: `tests/test_processing.py`
- Delete: `tests/test_data_loader.py`

- [ ] **Step 1: Confirm no imports from old modules remain in `src/`**

Run: `grep -rE "^from (processing|data_loader)" src/ tests/analysis tests/io || true`
Expected: no output.

- [ ] **Step 2: Run full test suite minus old files**

Run: `python3 -m pytest tests/analysis tests/io -v`
Expected: PASS (all tests from Tasks 2–7).

- [ ] **Step 3: Delete old modules and their tests (app.py still imports them; fix next)**

```bash
rm processing.py data_loader.py tests/test_processing.py tests/test_data_loader.py tests/conftest.py
```

Note: old `tests/conftest.py` is replaced by `tests/io/conftest.py` (new) so deleting the root conftest is safe.

- [ ] **Step 4: Patch `app.py` imports to use `src.*` (temporary; full rewrite in Task 17)**

In `app.py` change lines:

From:
```python
from data_loader import load_plate
from processing import build_grid, compute_band_rms, interpolate_grid
```

To:
```python
from src.io.plate_loader import load_plate, LoadResult
from src.analysis.grid import build_grid
from src.analysis.rms import compute_band_rms
from src.analysis.interpolation import interpolate_grid
```

And update the two `load_plate(...)` call-sites to unpack from `LoadResult`:

Find in `app.py`:
```python
plates["Platte 1"] = cached_load(folder1.strip())
```
Replace with:
```python
result = cached_load(folder1.strip())
plates["Platte 1"] = (result.hole_data, result.ref_df)
for w in result.warnings:
    st.warning(f"Platte 1: {w}")
```
Apply the same pattern to the `Platte 2` call-site.

- [ ] **Step 5: Verify app still imports cleanly**

Run: `python3 -c "import app"` — expect no import errors (Streamlit will print a runtime warning about running outside `streamlit run`; that's fine).

Run: `python3 -m pytest -q`
Expected: PASS (only analysis + io tests remain).

- [ ] **Step 6: Commit**

```bash
git add -A
git commit -m "refactor: remove old processing/data_loader in favor of src/ layers"
```

---

## Task 9: UI strings module

**Files:**
- Create: `src/ui/strings.py`
- Create: `tests/ui/__init__.py`
- Create: `tests/ui/test_strings.py`

- [ ] **Step 1: Write test**

`tests/ui/test_strings.py`:

```python
from __future__ import annotations
from src.ui import strings as S


def test_required_strings_exist():
    required = [
        "PAGE_TITLE",
        "SIDEBAR_HEADER",
        "FOLDER_PLATE_1",
        "FOLDER_PLATE_2",
        "FREQUENCY_BAND",
        "AXIS",
        "NORMALIZE",
        "SHARED_SCALE",
        "COLORSCALE",
        "PICK_FOLDER",
        "CSV_EXPORT",
        "ERROR_PATH_NOT_FOUND",
        "ERROR_EMPTY_FOLDER",
        "ERROR_CSV_READ",
        "ERROR_CSV_SCHEMA",
        "ERROR_CSV_CONTENT",
        "WAITING_FOR_FOLDER",
    ]
    for name in required:
        val = getattr(S, name)
        assert isinstance(val, str) and val.strip()


def test_error_path_format_has_placeholder():
    assert "{path}" in S.ERROR_PATH_NOT_FOUND
```

- [ ] **Step 2: Run to fail**

Run: `python3 -m pytest tests/ui/test_strings.py -v`
Expected: FAIL — module missing.

- [ ] **Step 3: Implement `src/ui/strings.py`**

```python
from __future__ import annotations

PAGE_TITLE = "Beschleunigungsverteilung"
APP_TITLE = "Beschleunigungsverteilung — Plattenanalyse"

SIDEBAR_HEADER = "Einstellungen"
FOLDER_PLATE_1 = "Platte 1 — Ordnerpfad"
FOLDER_PLATE_2 = "Platte 2 — Ordnerpfad (optional)"
PICK_FOLDER = "Ordner wählen"

FREQUENCY_BAND = "Frequenzband (Hz)"
AXIS = "Achse"
NORMALIZE = "Normalisiert (relativ zur Referenz)"
SHARED_SCALE = "Gemeinsame Farbskala"
COLORSCALE = "Farbskala"

CSV_EXPORT = "CSV exportieren"

LOADING_PLATE = "Lade {label} …"
WAITING_FOR_FOLDER = "Bitte mindestens einen Ordnerpfad eingeben."

ERROR_PATH_NOT_FOUND = "Pfad existiert nicht: {path}"
ERROR_NOT_A_DIR = "Pfad ist kein Ordner: {path}"
ERROR_EMPTY_FOLDER = "Ordner enthält keine Dateien im Format x{{N}}-y{{M}}.csv: {path}"
ERROR_CSV_READ = "CSV konnte nicht gelesen werden — Encoding/Trennzeichen unbekannt: {path}"
ERROR_CSV_SCHEMA = "Spalten fehlen in {path}: {missing}. Erwartet: Frequenz_Hz, PSD_X_g2Hz, PSD_Y_g2Hz, PSD_Z_g2Hz."
ERROR_CSV_CONTENT = "Datei {path} enthält keine auswertbaren Messwerte."
ERROR_GENERIC_PLATE = "{label} konnte nicht geladen werden: {detail}"

REF_METRIC_LABEL_NORMALIZED = "Normalisiert (Ref = 1.0)"
REF_METRIC_LABEL_ABS = "{value:.4f} g RMS"
REF_METRIC_HEADER = "{name} — Referenz"

COLORBAR_NORMALIZED = "Normalisiert"
COLORBAR_ABSOLUTE = "g RMS"

SPECTRUM_TITLE = "{name} — Bohrung ({x}, {y}) · Achse {axis}"
SPECTRUM_X_LABEL = "Frequenz (Hz)"
SPECTRUM_Y_LABEL_TMPL = "PSD {axis} (g²/Hz)"
SPECTRUM_TRACE_HOLE = "Bohrung ({x}, {y})"
SPECTRUM_TRACE_REF = "Referenz"

HEATMAP_X_LABEL = "x-Bohrung"
HEATMAP_Y_LABEL = "y-Bohrung"

WARN_NO_DATA_FOR_HOLE = "{name}: Keine Messdaten für Bohrung ({x}, {y})."
```

- [ ] **Step 4: Run to pass**

Run: `python3 -m pytest tests/ui/test_strings.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/ui/strings.py tests/ui/__init__.py tests/ui/test_strings.py
git commit -m "feat: centralize UI strings in src/ui/strings.py"
```

---

## Task 10: UI errors module (exception → message)

**Files:**
- Create: `src/ui/errors.py`
- Create: `tests/ui/test_errors.py`

- [ ] **Step 1: Write failing tests**

`tests/ui/test_errors.py`:

```python
from __future__ import annotations

from pathlib import Path

from src.io.schema import (
    InvalidPlateFolderError,
    CsvReadError,
    CsvSchemaError,
    CsvContentError,
    AccVizError,
)
from src.ui.errors import format_error


def test_format_invalid_folder_not_exists():
    exc = InvalidPlateFolderError(path=Path("/x"), reason="not_exists")
    msg = format_error(exc, plate_label="Platte 1")
    assert "Pfad existiert nicht" in msg
    assert "/x" in msg


def test_format_invalid_folder_empty():
    exc = InvalidPlateFolderError(path=Path("/x"), reason="empty")
    msg = format_error(exc, plate_label="Platte 1")
    assert "keine Dateien" in msg


def test_format_csv_read():
    exc = CsvReadError(path=Path("/a.csv"), reason="encoding")
    msg = format_error(exc, plate_label="Platte 1")
    assert "Encoding" in msg or "gelesen werden" in msg
    assert "/a.csv" in msg


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
```

- [ ] **Step 2: Run to fail**

Run: `python3 -m pytest tests/ui/test_errors.py -v`
Expected: FAIL.

- [ ] **Step 3: Implement `src/ui/errors.py`**

```python
from __future__ import annotations

from src.io.schema import (
    AccVizError,
    CsvContentError,
    CsvReadError,
    CsvSchemaError,
    InvalidPlateFolderError,
)
from src.ui import strings as S


def format_error(exc: AccVizError, *, plate_label: str) -> str:
    if isinstance(exc, InvalidPlateFolderError):
        if exc.reason == "not_exists":
            return S.ERROR_PATH_NOT_FOUND.format(path=exc.path)
        if exc.reason == "not_a_dir":
            return S.ERROR_NOT_A_DIR.format(path=exc.path)
        if exc.reason == "empty":
            return S.ERROR_EMPTY_FOLDER.format(path=exc.path)
    if isinstance(exc, CsvReadError):
        return S.ERROR_CSV_READ.format(path=exc.path)
    if isinstance(exc, CsvSchemaError):
        missing = ", ".join(sorted(exc.missing))
        return S.ERROR_CSV_SCHEMA.format(path=exc.path, missing=missing)
    if isinstance(exc, CsvContentError):
        return S.ERROR_CSV_CONTENT.format(path=exc.path)
    return S.ERROR_GENERIC_PLATE.format(label=plate_label, detail=str(exc))
```

- [ ] **Step 4: Run to pass**

Run: `python3 -m pytest tests/ui/test_errors.py -v`
Expected: PASS (6 tests).

- [ ] **Step 5: Commit**

```bash
git add src/ui/errors.py tests/ui/test_errors.py
git commit -m "feat: add UI error-message mapper for AccVizError"
```

---

## Task 11: `subprocess_utils` wrapper for Windows console suppression

**Files:**
- Create: `src/platform_utils/subprocess_utils.py`
- Create: `tests/platform_utils/__init__.py`
- Create: `tests/platform_utils/test_subprocess_utils.py`

- [ ] **Step 1: Write failing test**

`tests/platform_utils/test_subprocess_utils.py`:

```python
from __future__ import annotations

from unittest.mock import patch, MagicMock

from src.platform_utils import subprocess_utils


def test_run_hidden_sets_creation_flags_on_windows():
    with patch("src.platform_utils.subprocess_utils.sys") as mock_sys, \
         patch("src.platform_utils.subprocess_utils.subprocess") as mock_sp:
        mock_sys.platform = "win32"
        mock_sp.CREATE_NO_WINDOW = 0x08000000
        mock_sp.run = MagicMock(return_value=MagicMock(returncode=0))
        subprocess_utils.run_hidden(["foo"])
        kwargs = mock_sp.run.call_args.kwargs
        assert kwargs.get("creationflags") == 0x08000000


def test_run_hidden_no_flags_on_posix():
    with patch("src.platform_utils.subprocess_utils.sys") as mock_sys, \
         patch("src.platform_utils.subprocess_utils.subprocess") as mock_sp:
        mock_sys.platform = "darwin"
        mock_sp.run = MagicMock(return_value=MagicMock(returncode=0))
        subprocess_utils.run_hidden(["foo"])
        kwargs = mock_sp.run.call_args.kwargs
        assert "creationflags" not in kwargs
```

- [ ] **Step 2: Run to fail**

Run: `python3 -m pytest tests/platform_utils/test_subprocess_utils.py -v`
Expected: FAIL.

- [ ] **Step 3: Implement `src/platform_utils/subprocess_utils.py`**

```python
from __future__ import annotations

import subprocess
import sys
from typing import Any


def run_hidden(args: list[str], **kwargs: Any) -> subprocess.CompletedProcess:
    """Run a subprocess, suppressing the console window on Windows."""
    if sys.platform.startswith("win"):
        kwargs.setdefault("creationflags", getattr(subprocess, "CREATE_NO_WINDOW", 0))
    return subprocess.run(args, **kwargs)
```

- [ ] **Step 4: Run to pass**

Run: `python3 -m pytest tests/platform_utils/test_subprocess_utils.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/platform_utils/subprocess_utils.py tests/platform_utils/__init__.py tests/platform_utils/test_subprocess_utils.py
git commit -m "feat: add run_hidden subprocess wrapper for Windows"
```

---

## Task 12: Folder picker (PyInstaller-safe)

**Files:**
- Create: `src/platform_utils/folder_picker.py`
- Create: `tests/platform_utils/test_folder_picker.py`

- [ ] **Step 1: Write failing tests**

`tests/platform_utils/test_folder_picker.py`:

```python
from __future__ import annotations

from unittest.mock import patch, MagicMock

from src.platform_utils import folder_picker


def test_macos_uses_osascript():
    mock_proc = MagicMock(returncode=0, stdout="/Users/x/plate/\n", stderr="")
    with patch("src.platform_utils.folder_picker.sys") as mock_sys, \
         patch("src.platform_utils.folder_picker.run_hidden", return_value=mock_proc) as mock_run:
        mock_sys.platform = "darwin"
        path = folder_picker.pick_folder()
        assert path == "/Users/x/plate"
        assert mock_run.call_args.args[0][0] == "osascript"


def test_macos_nonzero_returns_none():
    mock_proc = MagicMock(returncode=1, stdout="", stderr="cancelled")
    with patch("src.platform_utils.folder_picker.sys") as mock_sys, \
         patch("src.platform_utils.folder_picker.run_hidden", return_value=mock_proc):
        mock_sys.platform = "darwin"
        assert folder_picker.pick_folder() is None


def test_windows_uses_tkinter_inprocess(monkeypatch):
    import sys as real_sys
    monkeypatch.setattr(folder_picker.sys, "platform", "win32", raising=False)

    mock_tk = MagicMock()
    mock_fd = MagicMock()
    mock_fd.askdirectory = MagicMock(return_value="C:/tmp/plate")
    monkeypatch.setitem(real_sys.modules, "tkinter", mock_tk)
    monkeypatch.setitem(real_sys.modules, "tkinter.filedialog", mock_fd)

    path = folder_picker.pick_folder()
    assert path == "C:/tmp/plate"


def test_windows_empty_selection_returns_none(monkeypatch):
    import sys as real_sys
    monkeypatch.setattr(folder_picker.sys, "platform", "win32", raising=False)

    mock_tk = MagicMock()
    mock_fd = MagicMock()
    mock_fd.askdirectory = MagicMock(return_value="")
    monkeypatch.setitem(real_sys.modules, "tkinter", mock_tk)
    monkeypatch.setitem(real_sys.modules, "tkinter.filedialog", mock_fd)

    assert folder_picker.pick_folder() is None
```

- [ ] **Step 2: Run to fail**

Run: `python3 -m pytest tests/platform_utils/test_folder_picker.py -v`
Expected: FAIL.

- [ ] **Step 3: Implement `src/platform_utils/folder_picker.py`**

```python
from __future__ import annotations

import importlib
import subprocess
import sys

from src.platform_utils.subprocess_utils import run_hidden

_APPLESCRIPT = (
    'tell application "System Events" to activate\n'
    'set chosenFolder to choose folder with prompt "Ordner wählen"\n'
    'POSIX path of chosenFolder'
)


def _pick_via_osascript() -> str | None:
    try:
        result = run_hidden(
            ["osascript", "-e", _APPLESCRIPT],
            capture_output=True,
            text=True,
            timeout=300,
        )
    except subprocess.TimeoutExpired:
        return None
    if result.returncode != 0:
        return None
    path = (result.stdout or "").strip().rstrip("/")
    return path or None


def _pick_via_tkinter() -> str | None:
    tk = importlib.import_module("tkinter")
    fd = importlib.import_module("tkinter.filedialog")
    root = tk.Tk()
    try:
        root.withdraw()
        try:
            root.attributes("-topmost", True)
        except Exception:
            pass
        path = fd.askdirectory(parent=root)
    finally:
        try:
            root.destroy()
        except Exception:
            pass
    return path or None


def pick_folder() -> str | None:
    if sys.platform == "darwin":
        return _pick_via_osascript()
    return _pick_via_tkinter()
```

- [ ] **Step 4: Run to pass**

Run: `python3 -m pytest tests/platform_utils/test_folder_picker.py -v`
Expected: PASS (4 tests).

- [ ] **Step 5: Commit**

```bash
git add src/platform_utils/folder_picker.py tests/platform_utils/test_folder_picker.py
git commit -m "feat: PyInstaller-safe folder picker (osascript mac, in-process tkinter win)"
```

---

## Task 13: Sidebar module + `Settings` dataclass

**Files:**
- Create: `src/ui/sidebar.py`
- Create: `tests/ui/test_sidebar.py`

- [ ] **Step 1: Write test for the Settings dataclass only (sidebar widget rendering is Streamlit-specific; smoke test covers that later)**

`tests/ui/test_sidebar.py`:

```python
from __future__ import annotations

from src.ui.sidebar import Settings


def test_settings_is_frozen():
    s = Settings(folders=[("Platte 1", "/a")], f_min=0, f_max=25000,
                 axis="X", normalize=False, shared_scale=True, colorscale="Viridis")
    try:
        s.f_min = 100  # type: ignore[misc]
    except Exception:
        return
    raise AssertionError("Settings should be frozen")


def test_settings_accepts_multiple_folders():
    s = Settings(folders=[("Platte 1", "/a"), ("Platte 2", "/b")],
                 f_min=0, f_max=100, axis="Y",
                 normalize=True, shared_scale=False, colorscale="Plasma")
    assert len(s.folders) == 2
    assert s.axis == "Y"
```

- [ ] **Step 2: Run to fail**

Run: `python3 -m pytest tests/ui/test_sidebar.py -v`
Expected: FAIL.

- [ ] **Step 3: Implement `src/ui/sidebar.py`**

```python
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

import streamlit as st

from src.platform_utils.folder_picker import pick_folder
from src.ui import strings as S

Axis = Literal["X", "Y", "Z"]


@dataclass(frozen=True)
class Settings:
    folders: list[tuple[str, str]]  # (label, raw path)
    f_min: int
    f_max: int
    axis: Axis
    normalize: bool
    shared_scale: bool
    colorscale: str


_COLORSCALES = ["Viridis", "Plasma", "Hot", "RdBu", "Cividis", "Turbo", "Inferno"]


def _normalize_path(raw: str) -> str:
    return raw.strip().strip('"').strip("'")


def _folder_input(label: str, key: str) -> str:
    if key not in st.session_state:
        st.session_state[key] = ""
    col_a, col_b = st.columns([3, 1])
    with col_b:
        st.write("")
        st.write("")
        if st.button("📁", key=f"pick_{key}", help=S.PICK_FOLDER):
            picked = pick_folder()
            if picked:
                st.session_state[key] = picked
                st.rerun()
    with col_a:
        st.text_input(label, key=key)
    return _normalize_path(st.session_state[key])


def render_sidebar() -> Settings:
    with st.sidebar:
        st.header(S.SIDEBAR_HEADER)
        p1 = _folder_input(S.FOLDER_PLATE_1, "folder1")
        p2 = _folder_input(S.FOLDER_PLATE_2, "folder2")

        f_min, f_max = st.slider(
            S.FREQUENCY_BAND, min_value=0, max_value=25000,
            value=(0, 25000), step=100,
        )
        axis = st.radio(S.AXIS, ["X", "Y", "Z"], horizontal=True)
        normalize = st.toggle(S.NORMALIZE, value=False)
        shared_scale = st.checkbox(S.SHARED_SCALE, value=True)
        colorscale = st.selectbox(S.COLORSCALE, _COLORSCALES)

    folders: list[tuple[str, str]] = []
    if p1:
        folders.append(("Platte 1", p1))
    if p2:
        folders.append(("Platte 2", p2))

    return Settings(
        folders=folders,
        f_min=int(f_min),
        f_max=int(f_max),
        axis=axis,  # type: ignore[arg-type]
        normalize=normalize,
        shared_scale=shared_scale,
        colorscale=colorscale,
    )
```

- [ ] **Step 4: Run tests**

Run: `python3 -m pytest tests/ui/test_sidebar.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/ui/sidebar.py tests/ui/test_sidebar.py
git commit -m "feat: add Settings dataclass + render_sidebar"
```

---

## Task 14: Heatmap module

**Files:**
- Create: `src/ui/heatmap.py`

- [ ] **Step 1: Implement `src/ui/heatmap.py`**

This module has no unit tests (Plotly figure construction is covered by the smoke test in Task 20). Smoke-testable in the running app.

```python
from __future__ import annotations

import numpy as np
import plotly.graph_objects as go

from src.ui import strings as S

HEATMAP_HEIGHT = 600
HOLE_MARKER_SIZE = 8
REF_STAR_SIZE = 14


def make_heatmap(
    grid: np.ndarray,
    *,
    title: str,
    colorscale: str,
    normalized: bool,
    hole_positions: list[tuple[int, int]],
    hole_values: list[float],
    ref_value: float | None,
    z_range: tuple[float, float] | None,
) -> go.Figure:
    nrows, ncols = grid.shape
    label = S.COLORBAR_NORMALIZED if normalized else S.COLORBAR_ABSOLUTE

    fig = go.Figure(
        go.Heatmap(
            z=grid.T,
            x=list(range(1, nrows + 1)),
            y=list(range(1, ncols + 1)),
            colorscale=colorscale,
            zmin=z_range[0] if z_range else None,
            zmax=z_range[1] if z_range else None,
            colorbar=dict(title=label),
            hoverongaps=False,
            hovertemplate=f"x=%{{x}}, y=%{{y}}<br>Interpoliert ({label})=%{{z:.4f}}<extra></extra>",
        )
    )
    fig.add_trace(go.Scatter(
        x=[x for (x, _) in hole_positions],
        y=[y for (_, y) in hole_positions],
        mode="markers",
        marker=dict(
            size=HOLE_MARKER_SIZE,
            color="rgba(255,255,255,0.4)",
            line=dict(color="rgba(0,0,0,0.7)", width=1.5),
        ),
        customdata=hole_values,
        hovertemplate=f"x=%{{x}}, y=%{{y}}<br>{label}=%{{customdata:.4f}}<extra></extra>",
        showlegend=False,
    ))
    if ref_value is not None:
        fig.add_trace(go.Scatter(
            x=[(nrows + 1) / 2],
            y=[(ncols + 1) / 2],
            mode="markers",
            marker=dict(
                size=REF_STAR_SIZE,
                symbol="star",
                color="rgba(255,255,0,0.9)",
                line=dict(color="black", width=1.5),
            ),
            customdata=[ref_value],
            hovertemplate=f"Referenz (Mitte)<br>{label}=%{{customdata:.4f}}<extra></extra>",
            showlegend=False,
        ))

    fig.update_layout(
        title=title,
        xaxis_title=S.HEATMAP_X_LABEL,
        yaxis_title=S.HEATMAP_Y_LABEL,
        height=HEATMAP_HEIGHT,
    )
    fig.update_yaxes(scaleanchor="x", scaleratio=1, constrain="domain", autorange="reversed")
    fig.update_xaxes(constrain="domain")
    return fig
```

- [ ] **Step 2: Sanity-import**

Run: `python3 -c "from src.ui.heatmap import make_heatmap"`
Expected: no error.

- [ ] **Step 3: Commit**

```bash
git add src/ui/heatmap.py
git commit -m "refactor: extract heatmap builder to src/ui/heatmap.py"
```

---

## Task 15: Spectrum module

**Files:**
- Create: `src/ui/spectrum.py`

- [ ] **Step 1: Implement `src/ui/spectrum.py`**

```python
from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from src.ui import strings as S

SPECTRUM_HEIGHT = 350


def render_spectrum(
    *,
    plate_name: str,
    x_hole: int,
    y_hole: int,
    axis: str,
    hole_df: pd.DataFrame,
    ref_df: pd.DataFrame | None,
    f_min: int,
    f_max: int,
) -> None:
    col_psd = f"PSD_{axis}_g2Hz"
    st.subheader(S.SPECTRUM_TITLE.format(name=plate_name, x=x_hole, y=y_hole, axis=axis))

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=hole_df["Frequenz_Hz"],
        y=hole_df[col_psd],
        name=S.SPECTRUM_TRACE_HOLE.format(x=x_hole, y=y_hole),
        line=dict(width=1.5),
    ))
    if ref_df is not None:
        fig.add_trace(go.Scatter(
            x=ref_df["Frequenz_Hz"],
            y=ref_df[col_psd],
            name=S.SPECTRUM_TRACE_REF,
            line=dict(color="grey", width=1, dash="dash"),
        ))
    fig.add_vrect(x0=f_min, x1=f_max, fillcolor="yellow", opacity=0.1, line_width=0)
    fig.update_layout(
        xaxis_title=S.SPECTRUM_X_LABEL,
        yaxis_title=S.SPECTRUM_Y_LABEL_TMPL.format(axis=axis),
        yaxis_type="log",
        height=SPECTRUM_HEIGHT,
        legend=dict(orientation="h"),
    )
    st.plotly_chart(fig, use_container_width=True)
```

- [ ] **Step 2: Sanity-import**

Run: `python3 -c "from src.ui.spectrum import render_spectrum"`

- [ ] **Step 3: Commit**

```bash
git add src/ui/spectrum.py
git commit -m "refactor: extract spectrum renderer to src/ui/spectrum.py"
```

---

## Task 16: CSV export module (TDD)

**Files:**
- Create: `src/ui/export.py`
- Create: `tests/ui/test_export.py`

- [ ] **Step 1: Write failing test**

`tests/ui/test_export.py`:

```python
from __future__ import annotations

import io
import math
import pandas as pd

from src.ui.export import build_export_dataframe


def _df(val):
    return pd.DataFrame({
        "Frequenz_Hz": [0.0, 1.0, 2.0],
        "PSD_X_g2Hz": [val] * 3,
        "PSD_Y_g2Hz": [val] * 3,
        "PSD_Z_g2Hz": [val] * 3,
    })


def test_export_contains_all_holes_and_plates():
    plates = {
        "Platte 1": ({(1, 1): _df(1e-3), (1, 2): _df(2e-3)}, _df(1e-3)),
        "Platte 2": ({(1, 1): _df(4e-3)}, None),
    }
    df = build_export_dataframe(plates, f_min=0, f_max=2, axis="X")
    assert set(df["plate"]) == {"Platte 1", "Platte 2"}
    assert len(df) == 3  # 2 + 1


def test_export_normalization_column_filled_when_ref_present():
    plates = {
        "Platte 1": ({(1, 1): _df(4e-3)}, _df(1e-3)),
    }
    df = build_export_dataframe(plates, f_min=0, f_max=2, axis="X")
    row = df.iloc[0]
    assert math.isclose(float(row["band_rms_normalized"]), 2.0, rel_tol=1e-6)


def test_export_normalization_empty_when_no_ref():
    plates = {"Platte 1": ({(1, 1): _df(4e-3)}, None)}
    df = build_export_dataframe(plates, f_min=0, f_max=2, axis="X")
    assert df.iloc[0]["band_rms_normalized"] == ""
```

- [ ] **Step 2: Run to fail**

Run: `python3 -m pytest tests/ui/test_export.py -v`
Expected: FAIL.

- [ ] **Step 3: Implement `src/ui/export.py`**

```python
from __future__ import annotations

import math
import pandas as pd
import streamlit as st

from src.analysis.rms import compute_band_rms
from src.ui import strings as S


def build_export_dataframe(
    plates: dict[str, tuple[dict[tuple[int, int], pd.DataFrame], pd.DataFrame | None]],
    *,
    f_min: int,
    f_max: int,
    axis: str,
) -> pd.DataFrame:
    rows = []
    for name, (hole_data, ref_df) in plates.items():
        ref_rms = (
            compute_band_rms(ref_df, f_min, f_max, axis) if ref_df is not None else None
        )
        for (x, y), df in sorted(hole_data.items()):
            rms_abs = compute_band_rms(df, f_min, f_max, axis)
            norm = ""
            if (
                ref_rms is not None
                and not math.isnan(ref_rms)
                and ref_rms > 0
                and not math.isnan(rms_abs)
            ):
                norm = rms_abs / ref_rms
            rows.append({
                "plate": name,
                "x": x,
                "y": y,
                "axis": axis,
                "f_min_hz": f_min,
                "f_max_hz": f_max,
                "band_rms_abs": rms_abs,
                "band_rms_normalized": norm,
            })
    return pd.DataFrame(rows)


def render_csv_export(plates, *, f_min: int, f_max: int, axis: str) -> None:
    df = build_export_dataframe(plates, f_min=f_min, f_max=f_max, axis=axis)
    csv_bytes = df.to_csv(index=False).encode("utf-8")
    st.sidebar.download_button(
        label=S.CSV_EXPORT,
        data=csv_bytes,
        file_name="beschleunigung_export.csv",
        mime="text/csv",
    )
```

- [ ] **Step 4: Run to pass**

Run: `python3 -m pytest tests/ui/test_export.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/ui/export.py tests/ui/test_export.py
git commit -m "feat: extract CSV export builder to src/ui/export.py"
```

---

## Task 17: Rewrite `app.py` as thin composition layer

**Files:**
- Modify: `app.py` (full rewrite)

- [ ] **Step 1: Replace `app.py` contents**

```python
from __future__ import annotations

import math

import numpy as np
import streamlit as st

from src.analysis.grid import build_grid
from src.analysis.interpolation import interpolate_grid
from src.analysis.rms import compute_band_rms
from src.io.plate_loader import LoadResult, load_plate
from src.io.schema import AccVizError
from src.ui import strings as S
from src.ui.errors import format_error
from src.ui.export import render_csv_export
from src.ui.heatmap import make_heatmap
from src.ui.sidebar import Settings, render_sidebar
from src.ui.spectrum import render_spectrum

st.set_page_config(page_title=S.PAGE_TITLE, layout="wide")
st.title(S.APP_TITLE)

settings: Settings = render_sidebar()

if not settings.folders:
    st.info(S.WAITING_FOR_FOLDER)
    st.stop()


def _folder_mtime_token(folder: str) -> float:
    from pathlib import Path
    p = Path(folder)
    if not p.exists():
        return 0.0
    mtimes = [f.stat().st_mtime for f in p.glob("*.csv")]
    return max(mtimes) if mtimes else 0.0


@st.cache_data(show_spinner=False)
def _cached_load(folder: str, mtime_token: float) -> LoadResult:
    return load_plate(folder)


plates: dict[str, tuple] = {}
for label, folder in settings.folders:
    try:
        with st.spinner(S.LOADING_PLATE.format(label=label)):
            result = _cached_load(folder, _folder_mtime_token(folder))
    except AccVizError as exc:
        st.error(format_error(exc, plate_label=label))
        st.stop()
    for w in result.warnings:
        st.warning(f"{label}: {w}")
    plates[label] = (result.hole_data, result.ref_df)

grids: dict[str, np.ndarray] = {}
ref_rms: dict[str, float] = {}
for name, (hole_data, ref_df) in plates.items():
    grids[name] = build_grid(hole_data, ref_df, settings.f_min, settings.f_max, settings.axis, settings.normalize)
    if ref_df is not None:
        val = compute_band_rms(ref_df, settings.f_min, settings.f_max, settings.axis)
        if not math.isnan(val):
            ref_rms[name] = val


def _ref_for_interp(name: str) -> float | None:
    val = ref_rms.get(name)
    if val is None:
        return None
    return 1.0 if settings.normalize else val


interp_grids = {name: interpolate_grid(g, _ref_for_interp(name)) for name, g in grids.items()}

all_values = [v for g in interp_grids.values() for v in g.flatten() if not np.isnan(v)]
z_range = (min(all_values), max(all_values)) if (settings.shared_scale and all_values) else None

cols = st.columns(len(plates))
click_state: dict[str, tuple[int, int] | None] = {}

for col, name in zip(cols, plates.keys()):
    with col:
        ref_val = ref_rms.get(name)
        if ref_val is not None:
            label = (
                S.REF_METRIC_LABEL_NORMALIZED
                if settings.normalize
                else S.REF_METRIC_LABEL_ABS.format(value=ref_val)
            )
            st.metric(S.REF_METRIC_HEADER.format(name=name), label)

        hole_data_plate, _ = plates[name]
        sparse_grid = grids[name]
        positions, values = [], []
        for (x, y) in hole_data_plate.keys():
            v = float(sparse_grid[x - 1, y - 1])
            if not np.isnan(v):
                positions.append((x, y))
                values.append(v)

        if ref_val is None:
            ref_marker = None
        else:
            ref_marker = 1.0 if settings.normalize else ref_val

        fig = make_heatmap(
            interp_grids[name],
            title=name,
            colorscale=settings.colorscale,
            normalized=settings.normalize,
            hole_positions=positions,
            hole_values=values,
            ref_value=ref_marker,
            z_range=z_range,
        )
        event = st.plotly_chart(fig, on_select="rerun", key=f"heatmap_{name}", use_container_width=True)
        clicked = None
        if event and event["selection"] and event["selection"]["points"]:
            pt = event["selection"]["points"][0]
            clicked = (int(pt["x"]), int(pt["y"]))
        click_state[name] = clicked

for name, clicked in click_state.items():
    if clicked is None:
        continue
    x_hole, y_hole = clicked
    hole_data, ref_df = plates[name]
    if (x_hole, y_hole) not in hole_data:
        st.warning(S.WARN_NO_DATA_FOR_HOLE.format(name=name, x=x_hole, y=y_hole))
        continue
    render_spectrum(
        plate_name=name,
        x_hole=x_hole,
        y_hole=y_hole,
        axis=settings.axis,
        hole_df=hole_data[(x_hole, y_hole)],
        ref_df=ref_df,
        f_min=settings.f_min,
        f_max=settings.f_max,
    )

render_csv_export(plates, f_min=settings.f_min, f_max=settings.f_max, axis=settings.axis)
```

- [ ] **Step 2: Smoke-run the app manually**

Run: `python3 -m streamlit run app.py`
Expected: Streamlit starts on `localhost:8501`; page loads with sidebar; entering a fixture folder shows heatmap; click → spectrum; CSV export button works.

Kill the server with Ctrl-C when satisfied.

- [ ] **Step 3: Full test suite green**

Run: `python3 -m pytest -q`
Expected: all tests pass.

- [ ] **Step 4: Commit**

```bash
git add app.py
git commit -m "refactor: rewrite app.py as thin composition layer"
```

---

## Task 18: UI smoke test using `streamlit.testing.v1.AppTest`

**Files:**
- Create: `tests/ui/test_smoke.py`
- Create: `tests/ui/fixtures/` (copy of a small plate folder)

- [ ] **Step 1: Create a fixture plate folder under `tests/ui/fixtures/plate/`**

```bash
mkdir -p tests/ui/fixtures/plate
```

Write a helper module that generates fixtures on demand (keeps repo small).

`tests/ui/conftest.py`:

```python
from __future__ import annotations

import pytest
from pathlib import Path

from tests.io.conftest import write_csv

ROWS = [(f, 1e-3, 2e-3, 3e-3) for f in (0.0, 1.0, 2.0, 3.0, 4.0)]


@pytest.fixture
def smoke_plate_folder(tmp_path) -> Path:
    write_csv(tmp_path / "x1-y1.csv", ROWS)
    write_csv(tmp_path / "x1-y2.csv", ROWS)
    write_csv(tmp_path / "x2-y1.csv", ROWS)
    write_csv(tmp_path / "Referenz.csv", ROWS)
    return tmp_path
```

- [ ] **Step 2: Write the smoke test**

`tests/ui/test_smoke.py`:

```python
from __future__ import annotations

from streamlit.testing.v1 import AppTest


def test_app_renders_without_folder(tmp_path):
    at = AppTest.from_file("app.py", default_timeout=30)
    at.run()
    assert not at.exception
    # Should show info message asking for folder
    assert any("Ordnerpfad" in info.value for info in at.info)


def test_app_loads_fixture_plate(smoke_plate_folder):
    at = AppTest.from_file("app.py", default_timeout=60)
    at.session_state["folder1"] = str(smoke_plate_folder)
    at.run()
    assert not at.exception
    # At least one metric (reference RMS) is rendered.
    assert len(at.metric) >= 1
```

- [ ] **Step 3: Run the smoke test**

Run: `python3 -m pytest tests/ui/test_smoke.py -v`
Expected: PASS.

If `AppTest.from_file` cannot resolve `app.py`, set `pythonpath` in `pyproject.toml` already covers it. If a `ModuleNotFoundError` for `streamlit.testing` occurs, the Streamlit version is <1.35 — upgrade first: `pip install -U 'streamlit>=1.35'`.

- [ ] **Step 4: Commit**

```bash
git add tests/ui/conftest.py tests/ui/test_smoke.py
git commit -m "test: add Streamlit AppTest smoke test"
```

---

## Task 19: PyInstaller entry (`packaging/entry.py`)

**Files:**
- Create: `packaging/__init__.py` (empty)
- Create: `packaging/entry.py`

- [ ] **Step 1: Implement `packaging/entry.py`**

```python
from __future__ import annotations

import os
import sys
import threading
import time
import webbrowser
from pathlib import Path


def _open_browser_delayed(url: str, delay: float = 1.5) -> None:
    time.sleep(delay)
    try:
        webbrowser.open(url)
    except Exception:
        pass


def main() -> None:
    from streamlit.web import bootstrap

    base = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent.parent))
    app_path = str(base / "app.py")
    os.chdir(base)

    threading.Thread(
        target=_open_browser_delayed,
        args=("http://localhost:8501",),
        daemon=True,
    ).start()

    bootstrap.run(
        app_path,
        is_hello=False,
        args=[],
        flag_options={
            "server.headless": True,
            "browser.gatherUsageStats": False,
            "server.port": 8501,
        },
    )


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Smoke-check that the entry starts Streamlit when run directly (as a regular Python script, not a bundle)**

Run: `python3 packaging/entry.py &` then `curl -sS http://localhost:8501/_stcore/health`
Expected: response body `ok`. Kill with `kill %1`.

- [ ] **Step 3: Commit**

```bash
git add packaging/__init__.py packaging/entry.py
git commit -m "feat: add PyInstaller entry for programmatic Streamlit launch"
```

---

## Task 20: PyInstaller spec file

**Files:**
- Create: `packaging/acc_viz.spec`

- [ ] **Step 1: Implement `packaging/acc_viz.spec`**

```python
# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec for acc_visualisation.
# Build: pyinstaller packaging/acc_viz.spec

from pathlib import Path
import sys

from PyInstaller.utils.hooks import collect_all, collect_data_files, collect_submodules

block_cipher = None

streamlit_datas, streamlit_bins, streamlit_hidden = collect_all("streamlit")
plotly_datas, plotly_bins, plotly_hidden = collect_all("plotly")
scipy_hidden = collect_submodules("scipy")
pandas_hidden = collect_submodules("pandas")

project_root = Path(SPECPATH).parent.resolve()

added_files = [
    (str(project_root / "app.py"), "."),
    (str(project_root / "src"), "src"),
]
added_files += streamlit_datas + plotly_datas

hidden = [
    "streamlit.web.bootstrap",
    "streamlit.runtime.scriptrunner.magic_funcs",
    "tkinter",
    "tkinter.filedialog",
] + streamlit_hidden + plotly_hidden + scipy_hidden + pandas_hidden

a = Analysis(
    [str(project_root / "packaging" / "entry.py")],
    pathex=[str(project_root)],
    binaries=streamlit_bins + plotly_bins,
    datas=added_files,
    hiddenimports=hidden,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="acc_viz",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    name="acc_viz",
)

if sys.platform == "darwin":
    app = BUNDLE(
        coll,
        name="acc_viz.app",
        icon=None,
        bundle_identifier="com.acc.visualisation",
        info_plist={
            "NSHighResolutionCapable": True,
            "LSBackgroundOnly": False,
        },
    )
```

- [ ] **Step 2: Commit (no build yet — build happens in the next task)**

```bash
git add packaging/acc_viz.spec
git commit -m "feat: add PyInstaller spec for acc_viz"
```

---

## Task 21: Build script with smoke test

**Files:**
- Create: `packaging/build.py`
- Modify: `requirements.txt` (add `pyinstaller>=6.0`)

- [ ] **Step 1: Add PyInstaller to `requirements.txt`**

Append:
```
pyinstaller>=6.0
```

- [ ] **Step 2: Implement `packaging/build.py`**

```python
from __future__ import annotations

import subprocess
import sys
import time
import urllib.request
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
SPEC = ROOT / "packaging" / "acc_viz.spec"
DIST = ROOT / "dist" / "acc_viz"


def _run(cmd: list[str], **kw) -> None:
    print("+", " ".join(cmd))
    subprocess.check_call(cmd, cwd=ROOT, **kw)


def _binary_path() -> Path:
    if sys.platform == "darwin":
        return ROOT / "dist" / "acc_viz.app" / "Contents" / "MacOS" / "acc_viz"
    if sys.platform.startswith("win"):
        return DIST / "acc_viz.exe"
    return DIST / "acc_viz"


def _smoke_test() -> None:
    bin_path = _binary_path()
    if not bin_path.exists():
        raise SystemExit(f"Built binary not found: {bin_path}")
    proc = subprocess.Popen([str(bin_path)])
    try:
        deadline = time.time() + 30
        last_err: Exception | None = None
        while time.time() < deadline:
            try:
                with urllib.request.urlopen("http://localhost:8501/_stcore/health", timeout=2) as r:
                    if r.status == 200:
                        print("Smoke test: health OK")
                        return
            except Exception as e:
                last_err = e
                time.sleep(1)
        raise SystemExit(f"Smoke test failed: {last_err}")
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            proc.kill()


def main() -> None:
    _run([sys.executable, "-m", "PyInstaller", "--noconfirm", str(SPEC)])
    _smoke_test()


if __name__ == "__main__":
    main()
```

- [ ] **Step 3: Local build test (Mac, on the dev machine)**

Run: `pip install -r requirements.txt && python3 packaging/build.py`
Expected: Build completes, binary in `dist/acc_viz.app`, smoke test prints `Smoke test: health OK`.

If Streamlit bootstrap complains about missing data files, inspect the warning and add the missing path to `streamlit_datas` in `packaging/acc_viz.spec` via `collect_data_files("streamlit", include_py_files=True)`.

- [ ] **Step 4: Commit**

```bash
git add requirements.txt packaging/build.py
git commit -m "feat: add PyInstaller build script with health-check smoke test"
```

---

## Task 22: GitHub Actions CI (tests + matrix bundle)

**Files:**
- Create: `.github/workflows/ci.yml`

- [ ] **Step 1: Implement CI workflow**

```yaml
name: CI

on:
  push:
    branches: [master, main]
  pull_request:

jobs:
  test:
    strategy:
      fail-fast: false
      matrix:
        os: [ubuntu-latest, macos-latest, windows-latest]
    runs-on: ${{ matrix.os }}
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"
      - name: Install deps
        run: |
          python -m pip install --upgrade pip
          pip install -r requirements.txt
      - name: Run tests
        run: python -m pytest -q

  build:
    needs: test
    strategy:
      fail-fast: false
      matrix:
        os: [macos-latest, windows-latest]
    runs-on: ${{ matrix.os }}
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"
      - name: Install deps
        run: |
          python -m pip install --upgrade pip
          pip install -r requirements.txt
      - name: Build bundle
        run: python packaging/build.py
      - name: Upload artifact
        uses: actions/upload-artifact@v4
        with:
          name: acc_viz-${{ matrix.os }}
          path: |
            dist/acc_viz/**
            dist/acc_viz.app/**
          if-no-files-found: ignore
```

- [ ] **Step 2: Commit**

```bash
git add .github/workflows/ci.yml
git commit -m "ci: add test + PyInstaller build matrix for mac/windows"
```

- [ ] **Step 3: Push and verify**

Run: `git push`
Verify on GitHub Actions tab that all three test jobs pass and both build jobs produce artifacts. Fix any platform-specific issues that surface (most likely: missing hidden imports — add to the spec).

---

## Final verification

- [ ] **Step 1: Full test suite green locally**

Run: `python3 -m pytest -q`
Expected: all tests pass.

- [ ] **Step 2: App runs via Streamlit CLI**

Run: `python3 -m streamlit run app.py`, load a real plate folder, click a hole, verify heatmap + spectrum + CSV export. Kill with Ctrl-C.

- [ ] **Step 3: Bundled app launches on host platform**

Run: `python3 packaging/build.py`, then launch `dist/acc_viz.app` (Mac) or `dist/acc_viz/acc_viz.exe` (Windows). Browser should open with the app.

- [ ] **Step 4: CI green on push**

All jobs on GitHub Actions pass and artifacts are uploaded for Mac + Windows.

---

## Spec Coverage Summary

| Spec Section | Covered by |
|---|---|
| Architecture | Tasks 1, 8 |
| PyInstaller deployment | Tasks 19, 20, 21, 22 |
| Folder picker PyInstaller-safe | Task 12 |
| Windows console suppression | Task 11 |
| CSV encoding/separator robust | Task 6 |
| Header auto-detect | Task 6 |
| Strict error mode | Task 7 |
| Exception hierarchy | Task 5 |
| UI error translation | Task 10 |
| Settings dataclass | Task 13 |
| UI modules (sidebar/heatmap/spectrum/export) | Tasks 13–16 |
| Thin app.py | Task 17 |
| UI strings centralized | Task 9 |
| mtime cache key | Task 17 (`_cached_load`) |
| Analysis tests | Tasks 2, 3, 4 |
| IO tests | Tasks 5, 6, 7 |
| Platform tests | Tasks 11, 12 |
| UI smoke test | Task 18 |
| Build smoke test | Task 21 |
| CI matrix | Task 22 |
