# Folder-Load Progress Feedback + C-Engine Parser — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Stop the Windows "Keine Rückmeldung" freeze when loading ~200 MB of measurement CSVs by (a) swapping the pandas parser to the C engine and (b) showing a cooperative modal `QProgressDialog` driven on the UI thread.

**Architecture:** The load loop stays on the UI thread (Variante ①) but pumps Qt events per file and updates a modal dialog; with the C engine each 3.3 MB file parses in ~tens of ms, so the window never reaches the 5 s freeze threshold. Progress flows through a Qt-free `Callable`; the Qt glue lives in a small `desktop/load_progress.py`. The load stays **synchronous from the caller's view**, so existing desktop tests stay valid.

**Tech Stack:** Python 3.10+, pandas (C parser), PySide6 (`QProgressDialog`, `QApplication.processEvents`), pytest (offscreen Qt fixture), pyright (CI gate, pinned 1.1.410).

**Spec:** `docs/superpowers/specs/2026-06-18-folder-load-progress-design.md`

**This plan was hardened by an adversarial agent review.** Key corrections baked in: pyright-clean closure factory (no `inner: …=None` + `def inner`); one global progress total computed up front with `base` advancing on **every** outcome (fixes backwards bar on a mid-folder error and the duplicate-folder stall); lazy dialog construction (no flicker / no widget on cache hits); a `_is_loading` re-entrancy guard (queued signals **do** fire during `processEvents`); and **Option-A cancel** = fully revert folder field **and** view to the last good state.

---

## File Structure

| File | Responsibility | Change |
|---|---|---|
| `src/io/schema.py` | CSV vocab + domain errors | Add `ProgressCallback` + `LoadCancelled` |
| `src/io/csv_reader.py` | Single-CSV reader | `engine="python"` → `engine="c"` |
| `src/io/plate_loader.py` | Load one plate folder | `_is_plate_file`, `count_plate_files`, `progress` + total |
| `src/core/pipeline.py` | Load orchestration | `_make_inner`, precomputed counts, base-advance-on-all-paths, propagate `LoadCancelled` |
| `src/core/strings.py` | German UI strings | 4 progress/cancel constants |
| `src/desktop/load_progress.py` | **New** Qt dialog driver | `load_with_progress` (lazy dialog) |
| `src/desktop/control_panel.py` | Settings panel | `folder_texts` / `restore_folder_texts` |
| `src/desktop/main_window.py` | Window / wiring | `_is_loading` guard + Option-A cancel |
| `tests/core/conftest.py` | Core test helpers | autouse `_LOAD_CACHE` reset fixture |

---

## Task 1: `LoadCancelled` exception + `ProgressCallback` type

**Files:**
- Modify: `src/io/schema.py`
- Test: `tests/io/test_schema.py`

- [ ] **Step 1: Write the failing test**

Append to `tests/io/test_schema.py`:

```python
def test_load_cancelled_is_plain_exception_not_accviz_error():
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

In `src/io/schema.py`, add to the imports at the top:

```python
from collections.abc import Callable
```

Append at the end of the file:

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
Expected: PASS (all)

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

Behavior-preserving refactor. The existing **11** `test_csv_reader` tests are the regression guard; we add one representative many-row test that must stay green **before and after** the swap (verified empirically: 12 pass under the C engine).

- [ ] **Step 1: Add a representative regression test**

Append to `tests/io/test_csv_reader.py`:

```python
def test_parses_many_rows_semicolon_decimal_comma(tmp_path):
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
Expected: PASS (12 tests) — proves the new test is valid before the change.

- [ ] **Step 3: Make the one-line change**

In `src/io/csv_reader.py`, in `read_measurement_csv`, change `engine="python"` to `engine="c"`:

```python
        df = pd.read_csv(
            io.StringIO(text),
            skiprows=header_idx,
            sep=sep,
            decimal=decimal,
            engine="c",
        )
```

- [ ] **Step 4: Run tests to verify they still pass**

Run: `pytest tests/io/test_csv_reader.py -v`
Expected: PASS (12) — identical behavior across encodings, separators, decimal comma, BOM, header offset, and all error paths.

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

Contract: `progress(i, total, name)` fires **once per file that will be parsed**, `i` 1-based and increasing, `total` constant (= hole files + optional reference), called **before** reading file `i`. `count_plate_files` MUST share the exact predicate `load_plate` uses (so the pipeline's `base` offset matches the emitted count).

- [ ] **Step 1: Write the failing tests**

Append to `tests/io/test_plate_loader.py`:

```python
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
    assert len(calls) == 4                     # stray not counted, not parsed
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/io/test_plate_loader.py::test_load_plate_reports_progress_once_per_file -v`
Expected: FAIL with `TypeError: load_plate() got an unexpected keyword argument 'progress'`

- [ ] **Step 3: Implement progress + total + shared predicate**

In `src/io/plate_loader.py`, update the schema import:

```python
from src.io.schema import InvalidPlateFolderError, ProgressCallback
```

Add the shared predicate + counter above `load_plate`:

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

Replace `load_plate`'s body (keep the existing docstring) with:

```python
def load_plate(
    folder: Path | str, *, progress: ProgressCallback | None = None
) -> LoadResult:
    folder_path = Path(folder)

    if not folder_path.exists():
        raise InvalidPlateFolderError(path=folder_path, reason="not_exists")
    if not folder_path.is_dir():
        raise InvalidPlateFolderError(path=folder_path, reason="not_a_dir")

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
Expected: PASS (all new + existing)

- [ ] **Step 5: Commit**

```bash
git add src/io/plate_loader.py tests/io/test_plate_loader.py
git commit -m "feat(io): per-file progress + count_plate_files in load_plate"
```

---

## Task 4: Global progress + cancel propagation in `load_plates`

**Files:**
- Modify: `src/core/pipeline.py`
- Test: `tests/core/test_pipeline.py`, `tests/core/conftest.py`

One monotonic bar `0..grand_total`; `base` advances by a folder's full size on **every** outcome (success/error) so a corrupt CSV mid-folder cannot drive the bar backwards or stall it. `_is_cached` is **removed** (the up-front sum is correct even for duplicate folders).

- [ ] **Step 1: Add the cache-reset fixture + write the failing tests**

Append to `tests/core/conftest.py`:

```python
import pytest

from src.core import pipeline


@pytest.fixture(autouse=True)
def _clear_load_cache():
    """Keep the module-level LRU from leaking state across tests."""
    pipeline._LOAD_CACHE.clear()
    yield
    pipeline._LOAD_CACHE.clear()
```

At the top of `tests/core/test_pipeline.py` add:

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
    assert [d for d, _ in seen] == [1, 2, 3, 4]
    assert all(t == 4 for _, t in seen)


def test_load_plates_cache_hit_reports_no_progress(tmp_path):
    from tests.core.conftest import make_plate_folder

    folder = make_plate_folder(tmp_path / "p1", {(0, 0): 1e-3, (1, 1): 4e-3})
    load_plates([("Platte 1", str(folder))])           # warm the LRU
    calls: list[str] = []
    load_plates([("Platte 1", str(folder))], progress=lambda d, t, n: calls.append(n))
    assert calls == []


def test_load_plates_progress_monotonic_when_a_folder_errors(tmp_path):
    from tests.core.conftest import make_plate_folder

    good = make_plate_folder(tmp_path / "p1", {(0, 0): 1e-3, (1, 1): 4e-3})     # 2 files
    bad = tmp_path / "p2"
    bad.mkdir()
    (bad / "x0-y0.csv").write_text("# junk\nFrequenz_Hz,PSD_X_g2Hz\n0.0,1e-3\n1.0,1e-3\n")
    seen: list[tuple[int, int]] = []
    out = load_plates(
        [("Platte 1", str(good)), ("Platte 2", str(bad))],
        progress=lambda d, t, n: seen.append((d, t)),
    )
    dones = [d for d, _ in seen]
    assert dones == [1, 2, 3]                  # monotonic, never backwards
    assert all(t == 3 for _, t in seen)        # grand_total stable
    assert "Platte 2" not in out.plates
    assert len(out.errors) == 1
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/core/test_pipeline.py::test_load_plates_propagates_cancellation -v`
Expected: FAIL with `TypeError: load_plates() got an unexpected keyword argument 'progress'`

- [ ] **Step 3: Implement the threading + aggregation**

In `src/core/pipeline.py`, update imports:

```python
from src.io.plate_loader import LoadResult, count_plate_files, load_plate
from src.io.schema import AccVizError, LoadCancelled, ProgressCallback
```

Add a pyright-clean closure factory next to `_cached_load`:

```python
def _make_inner(
    progress: ProgressCallback, base: int, grand_total: int
) -> ProgressCallback:
    """Offset a per-folder callback into the global 0..grand_total bar."""
    def inner(i: int, _total: int, name: str) -> None:
        progress(base + i, grand_total, name)

    return inner
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

Rewrite `load_plates`:

```python
def load_plates(
    folders: Sequence[tuple[str, str]], *, progress: ProgressCallback | None = None
) -> PlateLoad:
    plates: dict[str, PlateEntry] = {}
    warnings: list[str] = []
    errors: list[str] = []

    # One global progress bar 0..grand_total. Counts are taken once up front so
    # `base` can advance by a folder's full size on EVERY outcome (success OR
    # error), keeping the bar monotonic and always reaching the total.
    counts = (
        [count_plate_files(folder) for _, folder in folders]
        if progress is not None
        else []
    )
    grand_total = sum(counts)
    base = 0

    for idx, (label, folder) in enumerate(folders):
        inner = _make_inner(progress, base, grand_total) if progress is not None else None
        result: LoadResult | None = None
        try:
            result = _cached_load(folder, progress=inner)
        except LoadCancelled:
            raise  # MUST precede the AccVizError/Exception handlers
        except AccVizError as exc:
            _LOG.warning("Plate %s load failed: %s", label, exc)
            errors.append(format_error(exc, plate_label=label))
        except Exception as exc:  # defensive: surface unexpected errors
            _LOG.exception("Unexpected error loading plate %s", label)
            errors.append(S.ERROR_GENERIC_PLATE.format(label=label, detail=str(exc)))
        finally:
            if progress is not None:
                base += counts[idx]

        if result is None:
            continue
        for w in result.warnings:
            warnings.append(f"{label}: {w}")
        plates[label] = (result.hole_data, result.ref_df)

    return PlateLoad(plates=plates, warnings=warnings, errors=errors)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/core/test_pipeline.py -v`
Expected: PASS (all new + existing)

- [ ] **Step 5: Commit**

```bash
git add src/core/pipeline.py tests/core/test_pipeline.py tests/core/conftest.py
git commit -m "feat(core): one global cancellable progress bar in load_plates"
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
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/core/strings.py tests/core/test_strings.py
git commit -m "feat(core): add progress-dialog UI strings"
```

---

## Task 6: `load_with_progress` helper (lazy modal dialog)

**Files:**
- Create: `src/desktop/load_progress.py`
- Test: `tests/desktop/test_load_progress.py`

The dialog is constructed **lazily on the first progress tick**, so cache hits / tiny folders create no widget and never flicker. A `dialog_factory` seam lets tests inject a fake (no real widget).

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
    load = load_with_progress(None, [("Platte 1", str(folder))], dialog_factory=lambda: fake)
    assert load is not None
    assert "Platte 1" in load.plates
    assert fake.range == (0, 2)
    assert fake.values == [1, 2]
    assert fake.closed is True


def test_load_with_progress_no_files_creates_no_dialog(qapp, tmp_path):
    # A folder served from cache reports zero progress -> no widget at all.
    from tests.core.conftest import make_plate_folder
    from src.core.pipeline import load_plates

    folder = make_plate_folder(tmp_path / "p1", {(0, 0): 1e-3, (1, 1): 4e-3})
    load_plates([("Platte 1", str(folder))])           # warm cache
    created = {"n": 0}

    def factory():
        created["n"] += 1
        return FakeDialog()

    load = load_with_progress(None, [("Platte 1", str(folder))], dialog_factory=factory)
    assert load is not None
    assert created["n"] == 0                            # never constructed


def test_load_with_progress_cancel_returns_none(qapp, tmp_path):
    from tests.core.conftest import make_plate_folder

    folder = make_plate_folder(tmp_path / "p1", {(0, 0): 1e-3, (1, 1): 4e-3})
    fake = FakeDialog(cancel_after=1)
    load = load_with_progress(None, [("Platte 1", str(folder))], dialog_factory=lambda: fake)
    assert load is None
    assert fake.closed is True
```

> Note: the `qapp` fixture (offscreen) comes from `tests/desktop/conftest.py`; the `_clear_load_cache` autouse fixture from Task 4 lives in `tests/core/conftest.py` and does NOT apply here, so `test_load_with_progress_no_files_creates_no_dialog` warms and reads the cache within one test (order-independent).

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
    is built lazily on the first progress tick, so cache hits / small folders
    create no widget and never flicker.
    """
    def _default_factory() -> QProgressDialog:
        return QProgressDialog(S.LOAD_PROGRESS_TITLE, S.LOAD_CANCEL, 0, 0, parent)

    factory = dialog_factory or _default_factory
    holder: dict[str, QProgressDialog] = {}

    def on_progress(done: int, total: int, name: str) -> None:
        dlg = holder.get("dlg")
        if dlg is None:
            dlg = factory()
            dlg.setWindowModality(Qt.WindowModality.ApplicationModal)
            dlg.setMinimumDuration(400)
            dlg.setAutoClose(False)
            dlg.setAutoReset(False)
            dlg.setRange(0, total)
            holder["dlg"] = dlg
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
        dlg = holder.get("dlg")
        if dlg is not None:
            dlg.close()
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/desktop/test_load_progress.py -v`
Expected: PASS (all three)

- [ ] **Step 5: Commit**

```bash
git add src/desktop/load_progress.py tests/desktop/test_load_progress.py
git commit -m "feat(desktop): lazy modal load_with_progress dialog helper"
```

---

## Task 7: `ControlPanel` folder-text snapshot / restore

**Files:**
- Modify: `src/desktop/control_panel.py`
- Test: `tests/desktop/test_control_panel.py`

Needed for Option-A cancel: snapshot the raw folder field text and restore it **without** re-emitting `settingsChanged`.

- [ ] **Step 1: Write the failing tests**

Append to `tests/desktop/test_control_panel.py`:

```python
def test_folder_texts_round_trip(qapp):
    from src.desktop.control_panel import ControlPanel

    panel = ControlPanel()
    panel.set_folder(0, "/a")
    panel.set_folder(1, "/b")
    assert panel.folder_texts() == ["/a", "/b"]


def test_restore_folder_texts_emits_no_signal(qapp):
    from src.desktop.control_panel import ControlPanel

    panel = ControlPanel()
    fired: list[int] = []
    panel.settingsChanged.connect(lambda: fired.append(1))
    panel.restore_folder_texts(["/x", "/y"])
    assert panel.folder_texts() == ["/x", "/y"]
    assert fired == []
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/desktop/test_control_panel.py::test_folder_texts_round_trip -v`
Expected: FAIL with `AttributeError: 'ControlPanel' object has no attribute 'folder_texts'`

- [ ] **Step 3: Add the methods**

In `src/desktop/control_panel.py`, add to the `# --- programmatic setters` section:

```python
    def folder_texts(self) -> list[str]:
        """Return the raw text of each folder input (for snapshot/restore)."""
        return [edit.text() for edit in self._folder_edits]

    def restore_folder_texts(self, texts: list[str]) -> None:
        """Restore folder inputs without emitting settingsChanged."""
        for edit, text in zip(self._folder_edits, texts):
            edit.blockSignals(True)
            edit.setText(text)
            edit.blockSignals(False)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/desktop/test_control_panel.py -v`
Expected: PASS (all)

- [ ] **Step 5: Commit**

```bash
git add src/desktop/control_panel.py tests/desktop/test_control_panel.py
git commit -m "feat(desktop): folder-text snapshot/restore on ControlPanel"
```

---

## Task 8: Wire into `MainWindow._refresh` (guard + Option-A cancel)

**Files:**
- Modify: `src/desktop/main_window.py` (imports `:24-39`; `__init__` `:92-103`; `_refresh` `:107-138`)
- Test: `tests/desktop/test_main_window.py`

- [ ] **Step 1: Write the failing test**

Append to `tests/desktop/test_main_window.py`:

```python
def test_refresh_cancel_reverts_field_and_keeps_state(qapp, tmp_path, monkeypatch):
    from src.desktop import main_window as mw
    from src.core import strings as S
    from tests.core.conftest import make_plate_folder

    folder = make_plate_folder(tmp_path / "p1", {(0, 0): 1e-3, (1, 1): 4e-3})
    win = MainWindow()
    win.control_panel.set_folder(0, str(folder))     # successful load + analyze
    assert win._analysis is not None
    prior_analysis = win._analysis
    prior_load = win._load
    good_texts = win.control_panel.folder_texts()

    # Next reload is cancelled.
    monkeypatch.setattr(mw, "load_with_progress", lambda *a, **k: None)
    folder2 = make_plate_folder(tmp_path / "p2", {(0, 0): 2e-3, (1, 1): 5e-3})
    win.control_panel.set_folder(1, str(folder2))    # folders change -> reload -> cancel

    assert win._analysis is prior_analysis            # view untouched
    assert win._load is prior_load
    assert win.control_panel.folder_texts() == good_texts   # field reverted (Option A)
    assert S.LOAD_CANCELLED in win.statusBar().currentMessage()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/desktop/test_main_window.py::test_refresh_cancel_reverts_field_and_keeps_state -v`
Expected: FAIL — `AttributeError: module 'src.desktop.main_window' has no attribute 'load_with_progress'`

- [ ] **Step 3: Wire the helper in**

In `src/desktop/main_window.py`, remove `load_plates` from the `from src.core.pipeline import (...)` block:

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

Add the top-level helper import (so it is monkeypatchable as `main_window.load_with_progress`):

```python
from src.desktop.control_panel import ControlPanel
from src.desktop.export import prompt_export
from src.desktop.load_progress import load_with_progress
from src.desktop.manual_dialog import ManualDialog
```

In `__init__`, alongside the other state fields (near `self._settings: Settings | None = None`):

```python
        self._is_loading = False
        self._last_good_folder_texts = self._control_panel.folder_texts()
```

In `_refresh`, add the guard as the very first statement:

```python
    def _refresh(self) -> None:
        if self._is_loading:
            return
```

Replace the folder-load branch with:

```python
        folders_changed = prev is None or prev.folders != settings.folders
        load = self._load
        if folders_changed or load is None:
            self._is_loading = True
            try:
                loaded = load_with_progress(self, settings.folders)
            finally:
                self._is_loading = False
            if loaded is None:
                # Option-A cancel: fully revert folder field AND view to the last
                # good state (blockSignals prevents an immediate reload).
                self._control_panel.restore_folder_texts(self._last_good_folder_texts)
                self._settings = prev
                self.statusBar().showMessage(S.LOAD_CANCELLED, 6000)
                return
            self._last_good_folder_texts = self._control_panel.folder_texts()
            load = loaded
            self._load = load
            self.statusBar().clearMessage()
            for msg in load.errors:
                self.statusBar().showMessage(msg, 10000)
```

(The `WaitCursor` block around `analyze()` below is unchanged.)

- [ ] **Step 4: Run the desktop suite to verify it passes**

Run: `pytest tests/desktop/ -v`
Expected: PASS (new cancel test + all existing, including `test_refresh_loads_and_analyzes_real_plate` and `test_refresh_resets_override_cursor`)

- [ ] **Step 5: Commit**

```bash
git add src/desktop/main_window.py tests/desktop/test_main_window.py
git commit -m "feat(desktop): cancellable progress load with re-entrancy guard in MainWindow"
```

---

## Task 9: Full verification

**Files:** none (verification only)

- [ ] **Step 1: Run the entire test suite**

Run: `pytest -q`
Expected: PASS — baseline was **166**; this plan adds **13** tests → **~179**, no failures.

- [ ] **Step 2: Type-check (CI gate, pinned pyright 1.1.410)**

Run: `pyright`
Expected: 0 errors. (Watch the `_make_inner` factory and `result: LoadResult | None = None` — they exist specifically to keep pyright clean.)

- [ ] **Step 3: Headless app smoke test**

Run: `ACC_VIZ_SMOKE=1 python3 desktop_main.py`
Expected: exits 0 after ~1.5 s, logs "Desktop app started", no traceback.

- [ ] **Step 4: Manual check (if a real plate folder is available)**

`python3 desktop_main.py`, pick a 50–70-file folder. Verify: modal "Lade Messdateien…" after a moment, "Datei i von N" advances, window stays responsive (no "Keine Rückmeldung"), **Abbrechen** stops the load and reverts both the folder field and the view to the previous state, and re-loading the same folder shows no flicker (cache hit).

- [ ] **Step 5: Commit any verification fixes** (only if Steps 1–3 surfaced issues)

```bash
git add -A
git commit -m "fix: address verification findings for folder-load progress"
```

---

## Task 10: Integrate to master, then version bump + release (MINOR 0.5.1 → 0.6.0)

A new backward-compatible feature ⇒ MINOR bump. **Merge to `master` first**, then bump+tag on the integration commit (so `v0.6.0` is an ancestor of `master`, not stranded on the feature branch).

- [ ] **Step 1: Integrate the feature branch**

Use superpowers:finishing-a-development-branch to merge `feature/folder-load-progress` into `master` (direct merge, no PR — per the user's choice). Ensure `master` is checked out and green afterward:

Run: `git checkout master && git merge --no-ff feature/folder-load-progress && pytest -q`
Expected: clean merge, tests PASS.

- [ ] **Step 2: Confirm version + no existing tag**

Run: `grep -n '^version' pyproject.toml && git tag -l v0.6.0`
Expected: `version = "0.5.1"`, and `v0.6.0` not listed.

- [ ] **Step 3: Bump `pyproject.toml` + README badge**

`pyproject.toml`: `version = "0.5.1"` → `version = "0.6.0"`.
`README.md`: `version-0.5.1-blue` → `version-0.6.0-blue`.

- [ ] **Step 4: Verify consistency + tests green**

Run: `pytest -q && grep -rn "0.6.0" pyproject.toml README.md`
Expected: tests PASS; both files show `0.6.0`.

- [ ] **Step 5: Commit, tag, push (versioning sync — pre-authorized)**

```bash
git add pyproject.toml README.md
git commit -m "chore: bump version to 0.6.0"
git tag -a v0.6.0 -m "v0.6.0"
git push --follow-tags
```

---

## Notes for the executor

- **TDD discipline:** every task is red → green → commit. Task 2 is a behavior-preserving refactor, so its test is green before and after (regression guard, not red-first).
- **Progress convention:** `progress(i, total, name)` — 1-based `i`, called **before** reading file `i`. Locked by Tasks 3–4.
- **`LoadCancelled` ordering:** in `load_plates`, `except LoadCancelled: raise` MUST precede `except AccVizError` / `except Exception`.
- **`base` advances on every outcome** (the `finally`) — that is what keeps the bar monotonic when a folder errors mid-load and when the same folder is picked twice. Do not "optimize" it back behind a success check.
- **Lazy dialog + `_is_loading` guard** are load-bearing: queued signals fire during `processEvents` (empirically confirmed), so the guard prevents re-entrant `_refresh`, and lazy construction keeps cache hits widget-free and existing fast tests dialog-free.
- **Monkeypatch target:** `load_with_progress` is imported at module top in `main_window.py` so the cancel test can patch `main_window.load_with_progress`.
- **Out of scope (YAGNI):** background threads / parallel reads (Variante ②), `usecols`, moving `analyze()` off-thread.
```

