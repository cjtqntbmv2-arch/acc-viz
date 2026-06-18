# Folder-Load Progress Feedback + C-Engine Parser — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Stop the Windows "Keine Rückmeldung" freeze when loading ~200 MB measurement folders by (a) swapping the pandas parser to the C engine and (b) showing a cooperative modal progress dialog driven on the UI thread.

**Architecture:** The load loop stays on the UI thread (Variante ①) but pumps Qt events per file and updates a modal `QProgressDialog`; with the C engine each 3.3 MB file parses in ~tens of ms, so the window never reaches the 5 s freeze threshold. Progress flows through a Qt-free `Callable` so `core`/`io` stay UI-agnostic; the Qt glue lives in a small `desktop/load_progress.py` helper. The load remains **synchronous from the caller's view**, so existing desktop tests stay valid.

**Tech Stack:** Python 3.10+, pandas (C parser), PySide6 (`QProgressDialog`, `QApplication.processEvents`), pytest (+ offscreen Qt fixture).

**Spec:** `docs/superpowers/specs/2026-06-18-folder-load-progress-design.md`

---

## File Structure

| File | Responsibility | Change |
|---|---|---|
| `src/io/schema.py` | Shared CSV vocab + domain errors | Add `ProgressCallback` type + `LoadCancelled` exception |
| `src/io/csv_reader.py` | Robust single-CSV reader | `engine="python"` → `engine="c"` |
| `src/io/plate_loader.py` | Load one plate folder | Add `progress` param, file-count total, `_is_plate_file`/`count_plate_files` |
| `src/core/pipeline.py` | Frontend-agnostic load orchestration | Thread `progress` through cache, aggregate one global bar, propagate `LoadCancelled` |
| `src/core/strings.py` | German UI strings | 4 new progress/cancel constants |
| `src/desktop/load_progress.py` | **New** Qt glue: drive modal dialog | New file (`load_with_progress`) |
| `src/desktop/main_window.py` | Main window / pipeline wiring | Call `load_with_progress`, handle cancel |

Keeping the Qt dialog driver in its own `load_progress.py` (rather than inside `main_window.py`) keeps the GUI entry file lean (it is already 325 lines) **and** makes the dialog logic unit-testable without constructing the whole window.

---

## Task 1: `LoadCancelled` exception + `ProgressCallback` type

**Files:**
- Modify: `src/io/schema.py`
- Test: `tests/io/test_schema.py`

- [ ] **Step 1: Write the failing test**

Append to `tests/io/test_schema.py`:

```python
def test_load_cancelled_is_plain_exception_not_accviz_error():
    # LoadCancelled must NOT be an AccVizError: load_plates turns AccVizError
    # into per-plate error strings, but a cancellation has to propagate.
    from src.io.schema import LoadCancelled, AccVizError

    assert issubclass(LoadCancelled, Exception)
    assert not issubclass(LoadCancelled, AccVizError)


def test_progress_callback_alias_is_exported():
    from src.io import schema

    assert hasattr(schema, "ProgressCallback")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/io/test_schema.py::test_load_cancelled_is_plain_exception_not_accviz_error -v`
Expected: FAIL with `ImportError: cannot import name 'LoadCancelled'`

- [ ] **Step 3: Write minimal implementation**

In `src/io/schema.py`, add `Callable` to the typing imports at the top:

```python
from collections.abc import Callable
```

Then append at the end of the file:

```python
# (done_files, total_files, current_filename) — UI-agnostic progress signal.
ProgressCallback = Callable[[int, int, str], None]


class LoadCancelled(Exception):
    """Raised by a progress callback to abort an in-flight load.

    Deliberately **not** an :class:`AccVizError`: :func:`load_plates` converts
    ``AccVizError`` per plate into user-facing error strings, whereas a
    cancellation must propagate out instead of being swallowed.
    """
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/io/test_schema.py -v`
Expected: PASS (all, including the two new tests)

- [ ] **Step 5: Commit**

```bash
git add src/io/schema.py tests/io/test_schema.py
git commit -m "feat(io): add ProgressCallback type and LoadCancelled exception"
```

---

## Task 2: Swap CSV parser to the C engine

**Files:**
- Modify: `src/io/csv_reader.py:70-76`
- Test: `tests/io/test_csv_reader.py`

This is a behavior-preserving refactor. The existing 12 `test_csv_reader` tests are the regression guard; we add one representative many-row test (matching the real 3.3 MB shape) that must stay green **before and after** the swap.

- [ ] **Step 1: Add a representative regression test**

Append to `tests/io/test_csv_reader.py`:

```python
def test_parses_many_rows_semicolon_decimal_comma(tmp_path):
    # Mirrors a real measurement file: many rows, ';' separator, decimal comma.
    rows = [(float(i), 1e-3, 2e-3, 3e-3) for i in range(2000)]
    p = tmp_path / "x1-y1.csv"
    write_csv(p, rows, sep=";", decimal=",", encoding="cp1252")
    df = read_measurement_csv(p)
    assert len(df) == 2000
    assert list(df.columns) == ["Frequenz_Hz", "PSD_X_g2Hz", "PSD_Y_g2Hz", "PSD_Z_g2Hz"]
    assert math.isclose(df["PSD_Z_g2Hz"].iloc[-1], 3e-3)
```

- [ ] **Step 2: Establish green baseline (still on the python engine)**

Run: `pytest tests/io/test_csv_reader.py -v`
Expected: PASS (all, including the new test) — proves the test is valid before the change.

- [ ] **Step 3: Make the one-line change**

In `src/io/csv_reader.py`, inside `read_measurement_csv`, change the `pd.read_csv(...)` call:

```python
        df = pd.read_csv(
            io.StringIO(text),
            skiprows=header_idx,
            sep=sep,
            decimal=decimal,
            engine="c",
        )
```

(Only `engine="python"` → `engine="c"`. All of `skiprows`, single-char `sep`, and `decimal` are C-engine compatible.)

- [ ] **Step 4: Run tests to verify they still pass**

Run: `pytest tests/io/test_csv_reader.py -v`
Expected: PASS (all 13) — proves the swap preserves behavior across encodings, separators, decimal comma, BOM, header offset, and error paths.

- [ ] **Step 5: Commit**

```bash
git add src/io/csv_reader.py tests/io/test_csv_reader.py
git commit -m "perf(io): parse measurement CSVs with the pandas C engine"
```

---

## Task 3: Progress callback + file total in `load_plate`

**Files:**
- Modify: `src/io/plate_loader.py`
- Test: `tests/io/test_plate_loader.py`

Contract: `progress(i, total, name)` is called **once per file that will be parsed**, with `i` 1-based and increasing, `total` constant (= count of hole files + optional reference), `name` the file name. It is called **before** reading that file, so raising `LoadCancelled` from the callback aborts before the next read.

- [ ] **Step 1: Write the failing tests**

Append to `tests/io/test_plate_loader.py`:

```python
def test_load_plate_reports_progress_once_per_file(tmp_path):
    _populate_plate(tmp_path)  # 3 hole files + Referenz.csv = 4 files
    calls: list[tuple[int, int, str]] = []
    load_plate(tmp_path, progress=lambda done, total, name: calls.append((done, total, name)))
    dones = [c[0] for c in calls]
    assert len(calls) == 4
    assert dones == [1, 2, 3, 4]              # 1-based, monotonic, ends at total
    assert all(c[1] == 4 for c in calls)       # total constant
    assert all(c[2].lower().endswith(".csv") for c in calls)


def test_load_plate_without_progress_is_unchanged(tmp_path):
    _populate_plate(tmp_path)
    result = load_plate(tmp_path)              # no progress kwarg
    assert set(result.hole_data.keys()) == {(1, 1), (1, 2), (2, 1)}


def test_load_plate_cancel_aborts_before_reading_remaining(tmp_path):
    from src.io.schema import LoadCancelled

    _populate_plate(tmp_path)                  # 4 files
    seen: list[str] = []

    def cb(done, total, name):
        seen.append(name)
        if done == 2:
            raise LoadCancelled

    with pytest.raises(LoadCancelled):
        load_plate(tmp_path, progress=cb)
    assert len(seen) == 2                       # stopped at the 2nd file
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/io/test_plate_loader.py::test_load_plate_reports_progress_once_per_file -v`
Expected: FAIL with `TypeError: load_plate() got an unexpected keyword argument 'progress'`

- [ ] **Step 3: Implement progress + total in `load_plate`**

In `src/io/plate_loader.py`, update the import line:

```python
from src.io.schema import InvalidPlateFolderError, ProgressCallback
```

Add a shared predicate above `load_plate` (DRY — reused by `count_plate_files` and the loop):

```python
def _is_plate_file(entry: Path) -> bool:
    """True for files load_plate parses: a hole file or the reference file."""
    if not entry.is_file():
        return False
    name_lower = entry.name.lower()
    return name_lower == _REFERENCE_NAME or bool(_HOLE_PATTERN.match(entry.name))


def count_plate_files(folder: Path | str) -> int:
    """Number of files :func:`load_plate` would parse; 0 for a missing folder."""
    folder_path = Path(folder)
    if not folder_path.is_dir():
        return 0
    return sum(1 for entry in folder_path.iterdir() if _is_plate_file(entry))
```

Replace the body of `load_plate` (keep the docstring) with a version that collects the files first, then reports progress per file:

```python
def load_plate(
    folder: Path | str, *, progress: ProgressCallback | None = None
) -> LoadResult:
    folder_path = Path(folder)

    if not folder_path.exists():
        raise InvalidPlateFolderError(path=folder_path, reason="not_exists")
    if not folder_path.is_dir():
        raise InvalidPlateFolderError(path=folder_path, reason="not_a_dir")

    # Collect the files we will parse first so progress knows the total.
    to_parse = [entry for entry in sorted(folder_path.iterdir()) if _is_plate_file(entry)]
    total = len(to_parse)

    hole_data: dict[tuple[int, int], pd.DataFrame] = {}
    ref_df: pd.DataFrame | None = None
    warnings: list[str] = []

    for i, entry in enumerate(to_parse, start=1):
        if progress is not None:
            progress(i, total, entry.name)
        if entry.name.lower() == _REFERENCE_NAME:
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

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/io/test_plate_loader.py -v`
Expected: PASS (all, including the 3 new tests and the 7 existing ones)

- [ ] **Step 5: Commit**

```bash
git add src/io/plate_loader.py tests/io/test_plate_loader.py
git commit -m "feat(io): report per-file progress and expose count_plate_files in load_plate"
```

---

## Task 4: Thread progress through `pipeline.load_plates`

**Files:**
- Modify: `src/core/pipeline.py`
- Test: `tests/core/test_pipeline.py`

Aggregate into **one** monotonic bar `0..grand_total` across all cache-miss folders; cancellation propagates; cache hits report no progress.

- [ ] **Step 1: Write the failing tests**

At the top of `tests/core/test_pipeline.py`, add `pytest` to the imports:

```python
import pytest
```

Append these tests:

```python
def test_load_plates_propagates_cancellation(tmp_path):
    from tests.core.conftest import make_plate_folder
    from src.io.schema import LoadCancelled

    folder = make_plate_folder(tmp_path / "p1", {(0, 0): 1e-3, (1, 1): 4e-3})

    def cb(done, total, name):
        raise LoadCancelled

    with pytest.raises(LoadCancelled):
        load_plates([("Platte 1", str(folder))], progress=cb)


def test_load_plates_progress_is_one_global_bar_across_folders(tmp_path):
    from tests.core.conftest import make_plate_folder

    f1 = make_plate_folder(tmp_path / "p1", {(0, 0): 1e-3, (1, 1): 4e-3})       # 2 files
    f2 = make_plate_folder(tmp_path / "p2", {(0, 0): 1e-3}, ref_val=1e-3)        # 2 files
    seen: list[tuple[int, int]] = []
    load_plates(
        [("Platte 1", str(f1)), ("Platte 2", str(f2))],
        progress=lambda done, total, name: seen.append((done, total)),
    )
    totals = {t for _, t in seen}
    seq = [d for d, _ in seen]
    assert totals == {4}                 # single global total, not per-folder
    assert seq == [1, 2, 3, 4]           # monotonic to grand total


def test_load_plates_cache_hit_reports_no_progress(tmp_path):
    from tests.core.conftest import make_plate_folder

    folder = make_plate_folder(tmp_path / "p1", {(0, 0): 1e-3, (1, 1): 4e-3})
    load_plates([("Platte 1", str(folder))])           # warm the LRU cache
    calls: list[str] = []
    load_plates([("Platte 1", str(folder))], progress=lambda d, t, n: calls.append(n))
    assert calls == []                                  # served from cache
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/core/test_pipeline.py::test_load_plates_propagates_cancellation -v`
Expected: FAIL with `TypeError: load_plates() got an unexpected keyword argument 'progress'`

- [ ] **Step 3: Implement the threading + aggregation**

In `src/core/pipeline.py`, update the imports:

```python
from src.io.plate_loader import LoadResult, count_plate_files, load_plate
from src.io.schema import AccVizError, LoadCancelled, ProgressCallback
```

Add a cache-membership helper next to `_cached_load`:

```python
def _is_cached(folder: str) -> bool:
    """True when a current (folder, newest-mtime) entry is already in the LRU."""
    return (folder, _folder_mtime_token(folder)) in _LOAD_CACHE
```

Give `_cached_load` an optional `progress` it forwards on a miss only:

```python
def _cached_load(folder: str, *, progress: ProgressCallback | None = None) -> LoadResult:
    """Load a plate folder, memoized (LRU) by (folder, newest-csv-mtime)."""
    token = _folder_mtime_token(folder)
    key = (folder, token)
    cached = _LOAD_CACHE.get(key)
    if cached is not None:
        _LOAD_CACHE.move_to_end(key)
        return cached
    result = load_plate(folder, progress=progress)
    _LOAD_CACHE[key] = result
    if len(_LOAD_CACHE) > _CACHE_MAXSIZE:
        _LOAD_CACHE.popitem(last=False)
    return result
```

Rewrite `load_plates` to thread a global, offset progress and propagate cancellation:

```python
def load_plates(
    folders: Sequence[tuple[str, str]], *, progress: ProgressCallback | None = None
) -> PlateLoad:
    plates: dict[str, PlateEntry] = {}
    warnings: list[str] = []
    errors: list[str] = []

    # One global progress bar across folders that will actually be parsed
    # (cache hits contribute nothing — they return instantly).
    grand_total = 0
    if progress is not None:
        grand_total = sum(
            count_plate_files(folder) for _, folder in folders if not _is_cached(folder)
        )
    base = 0

    for label, folder in folders:
        was_cached = progress is None or _is_cached(folder)
        inner: ProgressCallback | None = None
        if progress is not None and not was_cached:
            def inner(i: int, _total: int, name: str, _base: int = base) -> None:
                progress(_base + i, grand_total, name)

        try:
            result = _cached_load(folder, progress=inner)
        except LoadCancelled:
            raise  # MUST precede the AccVizError/Exception handlers below
        except AccVizError as exc:
            _LOG.warning("Plate %s load failed: %s", label, exc)
            errors.append(format_error(exc, plate_label=label))
            continue
        except Exception as exc:  # defensive: surface unexpected errors
            _LOG.exception("Unexpected error loading plate %s", label)
            errors.append(S.ERROR_GENERIC_PLATE.format(label=label, detail=str(exc)))
            continue

        if progress is not None and not was_cached:
            base += count_plate_files(folder)
        for w in result.warnings:
            warnings.append(f"{label}: {w}")
        plates[label] = (result.hole_data, result.ref_df)

    return PlateLoad(plates=plates, warnings=warnings, errors=errors)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/core/test_pipeline.py -v`
Expected: PASS (all, including the 3 new tests)

- [ ] **Step 5: Commit**

```bash
git add src/core/pipeline.py tests/core/test_pipeline.py
git commit -m "feat(core): thread cancellable global progress through load_plates"
```

---

## Task 5: UI strings for the progress dialog

**Files:**
- Modify: `src/core/strings.py`
- Test: `tests/core/test_strings.py`

- [ ] **Step 1: Write the failing test**

Append to `tests/core/test_strings.py`:

```python
def test_load_progress_strings_present():
    assert S.LOAD_PROGRESS_TITLE
    assert "{i}" in S.LOAD_PROGRESS_LABEL
    assert "{n}" in S.LOAD_PROGRESS_LABEL
    assert S.LOAD_CANCEL
    assert S.LOAD_CANCELLED
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/core/test_strings.py::test_load_progress_strings_present -v`
Expected: FAIL with `AttributeError: module 'src.core.strings' has no attribute 'LOAD_PROGRESS_TITLE'`

- [ ] **Step 3: Add the constants**

Append to `src/core/strings.py`:

```python
# --- Lade-Fortschritt -------------------------------------------------------
LOAD_PROGRESS_TITLE = "Lade Messdateien…"
LOAD_PROGRESS_LABEL = "Datei {i} von {n}"
LOAD_CANCEL = "Abbrechen"
LOAD_CANCELLED = "Laden abgebrochen"
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/core/test_strings.py -v`
Expected: PASS (all)

- [ ] **Step 5: Commit**

```bash
git add src/core/strings.py tests/core/test_strings.py
git commit -m "feat(core): add progress-dialog UI strings"
```

---

## Task 6: `load_with_progress` helper (Qt dialog driver)

**Files:**
- Create: `src/desktop/load_progress.py`
- Test: `tests/desktop/test_load_progress.py`

The helper owns all Qt specifics (dialog, `processEvents`, `wasCanceled`) and returns `None` on cancel. A `dialog_factory` seam lets tests inject a fake dialog (no real widget needed).

- [ ] **Step 1: Write the failing tests**

Create `tests/desktop/test_load_progress.py`:

```python
from __future__ import annotations

from src.desktop.load_progress import load_with_progress


class FakeDialog:
    """Minimal stand-in for QProgressDialog recording the helper's calls."""

    def __init__(self, cancel_after: int | None = None) -> None:
        self.values: list[int] = []
        self.labels: list[str] = []
        self.range: tuple[int, int] | None = None
        self.closed = False
        self._cancel_after = cancel_after

    def setWindowModality(self, *_): pass
    def setMinimumDuration(self, *_): pass
    def setAutoClose(self, *_): pass
    def setAutoReset(self, *_): pass
    def setRange(self, lo, hi): self.range = (lo, hi)
    def setLabelText(self, text): self.labels.append(text)
    def setValue(self, value): self.values.append(value)
    def close(self): self.closed = True

    def wasCanceled(self) -> bool:
        return self._cancel_after is not None and len(self.values) >= self._cancel_after


def test_load_with_progress_drives_dialog_and_returns_load(qapp, tmp_path):
    from tests.core.conftest import make_plate_folder

    folder = make_plate_folder(tmp_path / "p1", {(0, 0): 1e-3, (1, 1): 4e-3})
    fake = FakeDialog()
    load = load_with_progress(
        None, [("Platte 1", str(folder))], dialog_factory=lambda: fake
    )
    assert load is not None
    assert "Platte 1" in load.plates
    assert fake.range == (0, 2)
    assert fake.values == [1, 2]        # one update per file
    assert fake.closed is True


def test_load_with_progress_cancel_returns_none(qapp, tmp_path):
    from tests.core.conftest import make_plate_folder

    folder = make_plate_folder(tmp_path / "p1", {(0, 0): 1e-3, (1, 1): 4e-3})
    fake = FakeDialog(cancel_after=1)   # report canceled right after the first file
    load = load_with_progress(
        None, [("Platte 1", str(folder))], dialog_factory=lambda: fake
    )
    assert load is None
    assert fake.closed is True
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/desktop/test_load_progress.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'src.desktop.load_progress'`

- [ ] **Step 3: Create the helper**

Create `src/desktop/load_progress.py`:

```python
from __future__ import annotations

"""Cooperative modal progress dialog for loading plate folders on the UI thread.

Owns every Qt specific of the loading UX (dialog lifecycle, ``processEvents``,
cancellation) so that :mod:`src.core.pipeline` and :mod:`src.io` stay Qt-free.
"""

from collections.abc import Callable, Sequence

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QProgressDialog, QWidget

from src.core import strings as S
from src.core.pipeline import PlateLoad, load_plates
from src.io.schema import LoadCancelled


def load_with_progress(
    parent: QWidget | None,
    folders: Sequence[tuple[str, str]],
    *,
    dialog_factory: Callable[[], QProgressDialog] | None = None,
) -> PlateLoad | None:
    """Load ``folders`` while driving a modal progress dialog.

    Returns the :class:`PlateLoad`, or ``None`` if the user cancelled. The dialog
    only becomes visible once loading exceeds ~400 ms, so cache hits and small
    folders never flicker.
    """
    def _default_factory() -> QProgressDialog:
        return QProgressDialog(S.LOAD_PROGRESS_TITLE, S.LOAD_CANCEL, 0, 0, parent)

    dlg = (dialog_factory or _default_factory)()
    dlg.setWindowModality(Qt.WindowModality.WindowModal)
    dlg.setMinimumDuration(400)
    dlg.setAutoClose(False)
    dlg.setAutoReset(False)

    range_set = {"done": False}

    def on_progress(done: int, total: int, name: str) -> None:
        if not range_set["done"]:
            dlg.setRange(0, total)
            range_set["done"] = True
        dlg.setValue(done)
        dlg.setLabelText(S.LOAD_PROGRESS_LABEL.format(i=done, n=total))
        QApplication.processEvents()
        if dlg.wasCanceled():
            raise LoadCancelled

    try:
        return load_plates(folders, progress=on_progress)
    except LoadCancelled:
        return None
    finally:
        dlg.close()
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/desktop/test_load_progress.py -v`
Expected: PASS (both)

- [ ] **Step 5: Commit**

```bash
git add src/desktop/load_progress.py tests/desktop/test_load_progress.py
git commit -m "feat(desktop): add load_with_progress modal dialog helper"
```

---

## Task 7: Wire `load_with_progress` into `MainWindow._refresh`

**Files:**
- Modify: `src/desktop/main_window.py:24-39` (imports) and `:126-138` (`_refresh` load branch)
- Test: `tests/desktop/test_main_window.py`

- [ ] **Step 1: Write the failing test**

Append to `tests/desktop/test_main_window.py`:

```python
def test_refresh_cancel_keeps_previous_state(qapp, tmp_path, monkeypatch):
    from src.desktop import main_window as mw
    from tests.core.conftest import make_plate_folder

    folder = make_plate_folder(tmp_path / "p1", {(0, 0): 1e-3, (1, 1): 4e-3})
    win = MainWindow()
    win.control_panel.set_folder(0, str(folder))   # successful load + analyze
    assert win._analysis is not None
    prior_analysis = win._analysis
    prior_load = win._load

    # Next reload is cancelled: stub the helper to report a cancellation.
    monkeypatch.setattr(mw, "load_with_progress", lambda *a, **k: None)
    folder2 = make_plate_folder(tmp_path / "p2", {(0, 0): 2e-3, (1, 1): 5e-3})
    win.control_panel.set_folder(1, str(folder2))  # folders change -> reload -> cancel

    assert win._analysis is prior_analysis          # view state untouched
    assert win._load is prior_load
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/desktop/test_main_window.py::test_refresh_cancel_keeps_previous_state -v`
Expected: FAIL — `AttributeError: module 'src.desktop.main_window' has no attribute 'load_with_progress'` (helper not imported yet)

- [ ] **Step 3: Wire the helper in**

In `src/desktop/main_window.py`, replace the `load_plates` import in the `from src.core.pipeline import (...)` block — i.e. remove `load_plates` from that import list — and add a top-level import (so it is monkeypatchable as `main_window.load_with_progress`):

```python
from src.desktop.control_panel import ControlPanel
from src.desktop.export import prompt_export
from src.desktop.load_progress import load_with_progress
from src.desktop.manual_dialog import ManualDialog
```

The pipeline import block becomes (note: no `load_plates`):

```python
from src.core.pipeline import (
    Analysis,
    PlateEntry,
    PlateLoad,
    analyze,
    measured_points,
    ref_marker,
)
```

In `_refresh`, replace the folder-load branch:

```python
        folders_changed = prev is None or prev.folders != settings.folders
        load = self._load
        if folders_changed or load is None:
            loaded = load_with_progress(self, settings.folders)
            if loaded is None:
                # Laden abgebrochen: vorherigen Zustand behalten und einen
                # erneuten (identischen) settingsChanged wieder laden lassen.
                self._settings = prev
                self.statusBar().showMessage(S.LOAD_CANCELLED, 6000)
                return
            load = loaded
            self._load = load
            self.statusBar().clearMessage()
            for msg in load.errors:
                self.statusBar().showMessage(msg, 10000)
```

- [ ] **Step 4: Run the desktop suite to verify it passes**

Run: `pytest tests/desktop/test_main_window.py -v`
Expected: PASS (all, including the new cancel test and the existing load/cursor tests)

- [ ] **Step 5: Commit**

```bash
git add src/desktop/main_window.py tests/desktop/test_main_window.py
git commit -m "feat(desktop): load folders via cancellable progress dialog in MainWindow"
```

---

## Task 8: Full verification

**Files:** none (verification only)

- [ ] **Step 1: Run the entire test suite**

Run: `pytest -q`
Expected: PASS, no failures (≈ existing count + 11 new tests).

- [ ] **Step 2: Type-check (CI gate)**

Run: `pyright`
Expected: 0 errors (matches the CI type-check gate).

- [ ] **Step 3: Headless app smoke test**

Run: `ACC_VIZ_SMOKE=1 python3 desktop_main.py`
Expected: exits 0 after ~1.5 s with a logged "Desktop app started" and no traceback.

- [ ] **Step 4: Manual check (if a real plate folder is available)**

Run: `python3 desktop_main.py`, pick a 50–70-file folder. Verify: modal "Lade Messdateien…" appears after a moment, the "Datei i von N" bar advances, the window stays responsive (no "Keine Rückmeldung"), and **Abbrechen** stops the load while keeping the prior view. Re-loading the same folder shows no dialog flicker (cache hit).

- [ ] **Step 5: Commit any verification fixes** (only if Steps 1–3 surfaced issues)

```bash
git add -A
git commit -m "fix: address verification findings for folder-load progress"
```

---

## Task 9: Version bump + release (MINOR: 0.5.1 → 0.6.0)

A new backward-compatible feature ⇒ MINOR bump per the project versioning rule.

**Files:**
- Modify: `pyproject.toml` (`version`), `README.md` (version badge)
- Test: `tests/test_packaging_build.py` (if it asserts the version — otherwise none)

- [ ] **Step 1: Confirm current version + no existing tag**

Run: `grep -n '^version' pyproject.toml && git tag -l v0.6.0`
Expected: `version = "0.5.1"`, and `v0.6.0` not listed.

- [ ] **Step 2: Bump `pyproject.toml`**

Change `version = "0.5.1"` → `version = "0.6.0"`.

- [ ] **Step 3: Bump the README badge**

In `README.md`, change `version-0.5.1-blue` → `version-0.6.0-blue`.

- [ ] **Step 4: Verify consistency + tests still green**

Run: `pytest -q && grep -rn "0.6.0" pyproject.toml README.md`
Expected: tests PASS; both files show `0.6.0`.

- [ ] **Step 5: Commit, tag, push**

```bash
git add pyproject.toml README.md
git commit -m "chore: bump version to 0.6.0"
git tag -a v0.6.0 -m "v0.6.0"
git push --follow-tags
```

(Per the project versioning rule this push is pre-authorized. Note: `main`/`master` integration of the feature branch happens via superpowers:finishing-a-development-branch **before** this tag if the team merges first — adjust the branch the tag lands on accordingly.)

---

## Notes for the executor

- **TDD discipline:** every task is red → green → commit. Task 2 is a behavior-preserving refactor, so its test is green before and after (it guards against regression rather than failing first).
- **Progress index convention:** `progress(i, total, name)` uses a **1-based** `i`, called **before** reading file `i`. Tests in Tasks 3–4 lock this in.
- **`LoadCancelled` ordering:** in `load_plates`, `except LoadCancelled: raise` MUST come before `except AccVizError` / `except Exception`, or cancellation gets turned into a per-plate error string.
- **Why the helper is injectable:** `dialog_factory` keeps the dialog driver testable without a real `QProgressDialog`; `load_with_progress` is imported at module top in `main_window.py` so it can be monkeypatched in the cancel test.
- **Out of scope (YAGNI):** background threads / parallel reads (Variante ②), `usecols`, moving `analyze()` off-thread.
