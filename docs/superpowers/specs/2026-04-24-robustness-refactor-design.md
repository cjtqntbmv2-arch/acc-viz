# Robustness, Error-Handling & Structure Refactor

**Status:** Draft
**Date:** 2026-04-24
**Scope:** Full refactor — modular restructure, robust CSV/IO, strict error handling, UI cleanup, PyInstaller deployment readiness (Windows + macOS), testing strategy.

## Goals

1. Make the app PyInstaller-bundleable and runnable as a standalone `.exe`/`.app` on Windows and macOS.
2. Make CSV loading robust to real-world encoding/separator/decimal variants (especially German Excel exports).
3. Replace broad `except Exception` with a typed exception hierarchy; strict failure mode on any CSV problem.
4. Restructure the codebase into clear layered modules so each file has one responsibility.
5. Establish a testing strategy that covers the testable core (analysis, IO) and includes a deployment smoke test.

## Non-Goals

- i18n / English UI (strings stay German, centralized in one file).
- Performance work beyond what falls out naturally.
- New analysis features.
- Auto-update mechanism for the bundled app.

---

## Architecture

Target layout:

```
acc_visualisation/
├── app.py                      # Thin Streamlit entry & page composition (~60 lines)
├── src/
│   ├── io/
│   │   ├── csv_reader.py       # Encoding/separator-robust CSV reader
│   │   ├── plate_loader.py     # load_plate(), header detection, strict validation
│   │   └── schema.py           # Required columns, exception hierarchy
│   ├── analysis/
│   │   ├── rms.py              # compute_band_rms
│   │   ├── grid.py             # build_grid
│   │   └── interpolation.py    # interpolate_grid
│   ├── ui/
│   │   ├── sidebar.py          # Sidebar widgets, session state, Settings dataclass
│   │   ├── heatmap.py          # make_heatmap
│   │   ├── spectrum.py         # Spectrum detail plot
│   │   ├── export.py           # CSV export
│   │   ├── errors.py           # Exception → user-message mapping
│   │   └── strings.py          # All German UI strings (central)
│   └── platform_utils/
│       ├── folder_picker.py    # pick_folder(), PyInstaller-safe
│       └── subprocess_utils.py # CREATE_NO_WINDOW, osascript wrapper
├── packaging/
│   ├── entry.py                # PyInstaller entry: programmatic Streamlit bootstrap
│   ├── acc_viz.spec            # PyInstaller spec (hidden imports, data files)
│   └── build.py                # Platform-aware build script (Win/Mac)
├── tests/
│   ├── analysis/
│   ├── io/
│   │   └── fixtures/
│   └── platform_utils/
└── requirements.txt
```

**Principles:**

- `app.py` only composes; it does not load, compute, or plot inline.
- `src/analysis/` is pure functions, no Streamlit imports. Fully unit-testable.
- `src/io/` owns all filesystem access and all CSV parsing. Throws typed exceptions.
- `src/ui/` is the only layer that imports Streamlit.
- `src/platform_utils/` is the only place with `subprocess`, `platform`, `sys.executable`.
- `packaging/` is build-time only; never imported at runtime.

---

## PyInstaller Deployment

**Problem:** Streamlit's CLI (`streamlit run app.py`) does not work inside a PyInstaller bundle because `sys.executable` points to the frozen binary, not a Python interpreter.

**Solution:** Programmatic Streamlit bootstrap via `streamlit.web.bootstrap`.

`packaging/entry.py`:

```python
import os, sys, threading, time, webbrowser
from pathlib import Path
from streamlit.web import bootstrap

def _open_browser_delayed(url: str, delay: float = 1.5):
    time.sleep(delay)
    webbrowser.open(url)

def main():
    base = Path(getattr(sys, "_MEIPASS", Path(__file__).parent.parent))
    app_path = str(base / "app.py")
    os.chdir(base)
    threading.Thread(target=_open_browser_delayed,
                     args=("http://localhost:8501",), daemon=True).start()
    bootstrap.run(app_path, is_hello=False, args=[], flag_options={
        "server.headless": True,
        "browser.gatherUsageStats": False,
    })
```

**Folder picker (PyInstaller-safe):** Current code invokes `sys.executable -c <script>`, which breaks in a frozen bundle. New approach:

- **macOS:** `osascript` (OS binary, always present).
- **Windows/Linux:** Import Tkinter directly in-process (no subprocess). Declared as PyInstaller `hiddenimport`.

`src/platform_utils/subprocess_utils.py` exposes a `run(...)` wrapper that sets `creationflags=subprocess.CREATE_NO_WINDOW` on Windows to suppress console flashes.

**Build pipeline (`packaging/build.py`):**

- Detects host platform, invokes PyInstaller with `packaging/acc_viz.spec`.
- `acc_viz.spec` declares:
  - `hiddenimports`: `streamlit.*`, `scipy.special._cdflib`, `plotly.*`, `tkinter` (Windows).
  - `datas`: Streamlit static assets (`streamlit/static/`, `streamlit/runtime/static/`), Plotly templates.
  - macOS: `.app` bundle with `NSHighResolutionCapable=True`.
  - Windows: `--onedir` (not `--onefile` — better startup time, fewer antivirus false positives).
- Post-build smoke test: launch the binary, poll `http://localhost:8501/_stcore/health` up to 30 s, terminate.

**CI (GitHub Actions):** Matrix `{windows-latest, macos-latest}` runs tests, builds bundle, runs smoke test, uploads artifact.

---

## IO Robustness

**CSV reader (`src/io/csv_reader.py`):**

1. **Path normalization:** strip surrounding quotes, convert to `Path`. Centralized at UI → IO boundary.
2. **Encoding detection:** try `utf-8-sig` → `utf-8` → `cp1252` → `latin-1`; otherwise raise `CsvReadError`.
3. **Separator detection:** sniff the header row for `;` / `,` / `\t` (count-maximum). No blind `sep=None` / Python engine.
4. **Header line detection:** scan first ~30 lines for a line containing `Frequenz_Hz`; use as header. Fallback: `skiprows=11`. Replaces the hard-coded `_HEADER_LINES = 11`.
5. **Decimal separator:** if separator is `;`, try `decimal=","`; else `"."`.
6. **Numeric coercion:** after load, `pd.to_numeric(errors="coerce")` on required columns; drop rows that became NaN.

Public API:

```python
def read_measurement_csv(path: Path) -> pd.DataFrame:
    """Reads a measurement CSV with robust encoding/separator handling.
    Raises CsvReadError, CsvSchemaError, CsvContentError."""
```

**Plate loader (`src/io/plate_loader.py`):**

- Validates folder exists and contains at least one `x{N}-y{M}.csv`.
- Case-insensitive match for `Referenz.csv` (relevant on Linux test hosts; Win/Mac are case-insensitive by default).
- Returns a `LoadResult` dataclass:

```python
@dataclass
class LoadResult:
    hole_data: dict[tuple[int, int], pd.DataFrame]
    ref_df: pd.DataFrame | None
    warnings: list[str]   # only for missing Referenz.csv
```

---

## Error Handling (Strict)

**Exception hierarchy (`src/io/schema.py`):**

```
AccVizError
├── InvalidPlateFolderError   # path missing / not a directory / no matching files
├── CsvReadError              # all encoding/separator attempts failed
├── CsvSchemaError            # required columns missing, header not found
└── CsvContentError           # < 2 valid rows, all values NaN, etc.
```

All carry structured context: `path`, `reason`, optionally `expected` / `found`.

**Strict mode:** Any CSV that fails to read or is missing required columns aborts the load. No silent skipping of individual hole files.

**Warnings (load continues):**

- `Referenz.csv` missing → UI disables `normalize` toggle, shows warning banner.

**UI error translation (`src/ui/errors.py`):** Central `render_error(exc, plate_label)` maps exceptions to user-facing German messages via `st.error(...)` followed by `st.stop()` at the top level of `app.py`.

| Exception (reason)                         | User message                                                      |
|--------------------------------------------|-------------------------------------------------------------------|
| `InvalidPlateFolderError(not_exists)`      | „Pfad existiert nicht: `{path}`"                                  |
| `InvalidPlateFolderError(empty)`           | „Ordner enthält keine Dateien im Format `x{N}-y{M}.csv`"          |
| `CsvReadError`                             | „CSV konnte nicht gelesen werden — Encoding/Trennzeichen unbekannt: `{path}`" |
| `CsvSchemaError(missing=...)`              | „Spalten fehlen in `{path}`: {missing}. Erwartet: …"              |
| `CsvContentError`                          | „Datei `{path}` enthält keine auswertbaren Messwerte"             |

**Analysis edge cases (`src/analysis/rms.py`):**

- `f_min == f_max` → return `NaN`.
- All PSD values NaN in band → return `NaN`.
- Band fully outside data range → return `NaN`, UI surfaces as a warning.

No `st.stop()` inside `src/`. Only `app.py` decides to stop.

---

## UI & Consistency

**`app.py` target (~60 lines):**

```python
st.set_page_config(...)
st.title(...)
settings = render_sidebar()
plates = load_plates(settings.folders)
grids, interp, refs = compute_all(plates, settings)
render_heatmaps(plates.keys(), interp, grids, refs, settings)
render_spectra(click_state, plates, settings)
render_csv_export(plates, settings)
```

**Settings dataclass (`src/ui/sidebar.py`):**

```python
@dataclass(frozen=True)
class Settings:
    folders: list[tuple[str, str]]   # (label, path)
    f_min: int
    f_max: int
    axis: Literal["X", "Y", "Z"]
    normalize: bool
    shared_scale: bool
    colorscale: str
```

Replaces the current scattered module-scope variables. Plot functions take this typed object.

**Heatmap (`src/ui/heatmap.py`):**

- Signature: `make_heatmap(grid, *, title, settings, hole_positions, hole_values, ref_value, z_range)`.
- `z_range: tuple[float, float] | None` is passed in explicitly — no reliance on module-scope `z_min`/`z_max`.
- Constants at top: `HEATMAP_HEIGHT`, `HOLE_MARKER_SIZE`, `REF_STAR_SIZE`.
- Parameter/variable shadowing of `colorscale` is eliminated by using `settings.colorscale`.

**Caching:**

- `@st.cache_data` key includes a `mtime_token` (max mtime of `.csv` files in folder), computed cheaply before the cached call. Stale caches when files change.

**Consistency items that ride along:**

- `pathlib.Path` everywhere; no string path concatenation.
- `from __future__ import annotations` in each module; Python 3.10+.
- Module docstrings (1–2 lines). Function docstrings only where semantics are non-obvious.
- All German UI strings in `src/ui/strings.py`.

---

## Testing

**`tests/analysis/`** (migrated from existing `test_processing.py`):

- `test_rms.py`: trapezoidal integration vs. hand calculation; edge cases (`f_min == f_max`, band outside data, all NaN, < 2 points).
- `test_grid.py`: dimensions, normalization with/without reference, reference RMS = 0, reference NaN.
- `test_interpolation.py`: < 3 points → grid unchanged; reference center used; nearest fill for NaNs.

**`tests/io/`** (new):

- `test_csv_reader.py`: fixtures for encoding/separator matrix (UTF-8 + `,`, UTF-8-BOM, cp1252 + `;` + `decimal=","`, latin-1), malformed file → `CsvReadError`, header not at line 12 → detected.
- `test_plate_loader.py`: empty folder → `InvalidPlateFolderError`; missing required columns → `CsvSchemaError`; missing `Referenz.csv` → warning but result; non-matching filenames → ignored.
- Fixtures: small real CSVs (2–3 data rows) under `tests/io/fixtures/`. No mocking of pandas.

**`tests/platform_utils/`** (lightweight):

- `test_folder_picker.py`: mocks `subprocess.run` / Tkinter; asserts correct branch per `sys.platform`, timeout/error → `None`.

**UI smoke (`tests/ui/`):**

- One end-to-end test using `streamlit.testing.v1.AppTest` (requires Streamlit ≥ 1.35, already pinned): loads app with a fixture folder, asserts no exceptions, sidebar widgets present, at least one heatmap rendered.

**Build smoke:**

- Post-PyInstaller: launch binary, poll `/_stcore/health` (max 30 s), terminate. Runs per platform in CI.

**Conventions:**

- `pytest`. Fixtures in per-subfolder `conftest.py`.
- Realistic coverage target ~80 % on `src/analysis/` and `src/io/`; not measured or enforced.

---

## Out of Scope (explicitly)

- Auto-update for bundled app.
- Code signing / notarization (macOS Gatekeeper will warn; user right-clicks to open on first launch). Document in a future packaging note if needed.
- English UI / i18n framework.
- Logging framework (strict mode + clear error messages cover current needs).
