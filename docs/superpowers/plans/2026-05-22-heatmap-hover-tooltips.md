# Heatmap Hover Tooltips Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add Plotly-parity hover tooltips to the matplotlib desktop heatmap — measured points (coords + measured gRMS), interpolated cells (coords + interpolated value) and the reference star (reference value).

**Architecture:** A pure `resolve_hover(...)` function maps a cursor data-coordinate to tooltip text (priority: reference star → measured hole → interpolated cell → none), reusing the existing `nearest_cell` snapping. A `motion_notify_event` handler on `HeatmapCanvas` calls it and shows/hides a native `QToolTip` — no figure redraws on mouse move. `render_grid` stores the hover data (grid, hole lookup, reference value, normalized flag) on the instance.

**Tech Stack:** Python, PySide6 (Qt: `QToolTip`, `QCursor`), matplotlib (`FigureCanvasQTAgg`, `motion_notify_event`), NumPy, pytest.

---

### Task 1: Add hover tooltip string templates

**Files:**
- Modify: `src/ui/strings.py` (near `HEATMAP_X_LABEL` / `HEATMAP_Y_LABEL`, lines 49-50)

- [ ] **Step 1: Add the three template constants**

Insert directly after the `HEATMAP_Y_LABEL = "y-Bohrung"` line:

```python
HEATMAP_HOVER_MEASURED = "x={x}, y={y}\n{label}={value:.4f}"
HEATMAP_HOVER_INTERPOLATED = "x={x}, y={y}\nInterpoliert ({label})={value:.4f}"
HEATMAP_HOVER_REFERENCE = "Referenz (Mitte)\n{label}={value:.4f}"
```

These mirror the Plotly `hovertemplate` strings in `src/ui/heatmap.py` (`<br>` → `\n`). `label` is filled with `S.COLORBAR_NORMALIZED` ("Normalisiert") or `S.COLORBAR_ABSOLUTE` ("g RMS").

- [ ] **Step 2: Verify it imports**

Run: `python3 -c "from src.ui import strings as S; print(S.HEATMAP_HOVER_MEASURED.format(x=1, y=2, label='g RMS', value=0.12345))"`
Expected: `x=1, y=2` newline `g RMS=0.1235`

- [ ] **Step 3: Commit**

```bash
git add src/ui/strings.py
git commit -m "feat: add heatmap hover tooltip string templates"
```

---

### Task 2: Implement the pure `resolve_hover` function

**Files:**
- Modify: `src/desktop/plots/heatmap_canvas.py` (add module function after `nearest_cell`, ~line 71)
- Test: `tests/desktop/test_heatmap_canvas.py`

- [ ] **Step 1: Write the failing tests**

Add to `tests/desktop/test_heatmap_canvas.py`. Update the import at the top to include `resolve_hover`:

```python
from src.desktop.plots.heatmap_canvas import (
    HeatmapCanvas,
    colorscale_to_cmap,
    nearest_cell,
    resolve_hover,
)
```

Then add these tests (in the "pure helpers" section):

```python
def _grid():
    # grid[x, y]; (1,0) is NaN to represent an interpolation gap.
    return np.array([[1.0, 2.0], [np.nan, 4.0]])


def test_resolve_hover_measured_point():
    text = resolve_hover(
        0.05, 0.0,
        grid=_grid(),
        hole_lookup={(0, 0): 1.5},
        ref_value=None,
        normalized=False,
    )
    assert text == "x=0, y=0\ng RMS=1.5000"


def test_resolve_hover_interpolated_cell():
    text = resolve_hover(
        1.0, 1.0,
        grid=_grid(),
        hole_lookup={},
        ref_value=None,
        normalized=False,
    )
    assert text == "x=1, y=1\nInterpoliert (g RMS)=4.0000"


def test_resolve_hover_nan_gap_returns_none():
    # cell (1, 0) is NaN and not a measured hole.
    assert resolve_hover(
        1.0, 0.0, grid=_grid(), hole_lookup={}, ref_value=None, normalized=False,
    ) is None


def test_resolve_hover_out_of_bounds_returns_none():
    assert resolve_hover(
        5.0, 0.0, grid=_grid(), hole_lookup={}, ref_value=None, normalized=False,
    ) is None
    assert resolve_hover(
        None, None, grid=_grid(), hole_lookup={}, ref_value=None, normalized=False,
    ) is None


def test_resolve_hover_reference_center_takes_priority():
    # 2x2 grid -> center at (0.5, 0.5); ref_value present.
    text = resolve_hover(
        0.5, 0.5,
        grid=_grid(),
        hole_lookup={(0, 0): 1.5},
        ref_value=0.8,
        normalized=False,
    )
    assert text == "Referenz (Mitte)\ng RMS=0.8000"


def test_resolve_hover_reference_none_falls_back_to_cell():
    # Near center but no reference -> snaps to a cell instead.
    text = resolve_hover(
        0.4, 0.4,
        grid=_grid(),
        hole_lookup={(0, 0): 1.5},
        ref_value=None,
        normalized=False,
    )
    assert text == "x=0, y=0\ng RMS=1.5000"


def test_resolve_hover_normalized_label():
    text = resolve_hover(
        1.0, 1.0,
        grid=_grid(),
        hole_lookup={},
        ref_value=None,
        normalized=True,
    )
    assert text == "x=1, y=1\nInterpoliert (Normalisiert)=4.0000"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3 -m pytest tests/desktop/test_heatmap_canvas.py -k resolve_hover -v`
Expected: FAIL — `ImportError: cannot import name 'resolve_hover'`

- [ ] **Step 3: Implement `resolve_hover`**

Add this module-level function in `src/desktop/plots/heatmap_canvas.py`, immediately after the `nearest_cell` function (before the `class HeatmapCanvas` line). Note the existing imports already include `numpy as np` and `from src.ui import strings as S`.

```python
def resolve_hover(
    xdata: float | None,
    ydata: float | None,
    *,
    grid: np.ndarray,
    hole_lookup: dict[tuple[int, int], float],
    ref_value: float | None,
    normalized: bool,
) -> str | None:
    """Tooltip text for a cursor data-coordinate over the heatmap, or ``None``.

    Priority: reference star (near center) > measured hole > interpolated cell.
    NaN/gap cells and positions outside the grid return ``None`` (Plotly parity
    with ``hoverongaps=False``).
    """
    if xdata is None or ydata is None:
        return None

    nrows, ncols = grid.shape
    label = S.COLORBAR_NORMALIZED if normalized else S.COLORBAR_ABSOLUTE

    # 1. Reference star at the geometric center takes priority (drawn on top).
    if ref_value is not None:
        cx, cy = (nrows - 1) / 2, (ncols - 1) / 2
        if (xdata - cx) ** 2 + (ydata - cy) ** 2 < 0.25:  # within radius 0.5
            return S.HEATMAP_HOVER_REFERENCE.format(label=label, value=ref_value)

    cell = nearest_cell(xdata, ydata, nrows, ncols)
    if cell is None:
        return None
    x, y = cell

    # 2. Measured hole.
    if (x, y) in hole_lookup:
        return S.HEATMAP_HOVER_MEASURED.format(
            x=x, y=y, label=label, value=hole_lookup[(x, y)]
        )

    # 3. Interpolated cell (skip NaN gaps).
    value = grid[x, y]
    if np.isfinite(value):
        return S.HEATMAP_HOVER_INTERPOLATED.format(
            x=x, y=y, label=label, value=float(value)
        )
    return None
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python3 -m pytest tests/desktop/test_heatmap_canvas.py -k resolve_hover -v`
Expected: PASS (7 tests)

- [ ] **Step 5: Commit**

```bash
git add src/desktop/plots/heatmap_canvas.py tests/desktop/test_heatmap_canvas.py
git commit -m "feat: add resolve_hover for heatmap tooltip text"
```

---

### Task 3: Wire the motion handler + store hover data in `render_grid`

**Files:**
- Modify: `src/desktop/plots/heatmap_canvas.py` (imports; `__init__`; `render_grid`; new `_on_motion`)
- Test: `tests/desktop/test_heatmap_canvas.py`

- [ ] **Step 1: Write the failing test**

Add to the "canvas widget" section of `tests/desktop/test_heatmap_canvas.py`:

```python
def test_heatmap_canvas_motion_shows_tooltip(qapp):
    canvas = HeatmapCanvas()
    grid = np.array([[1.0, 2.0], [3.0, 4.0]])
    canvas.render_grid(
        grid, plate_name="Platte 1", title="t", colorscale="Viridis",
        normalized=False, hole_positions=[(0, 0)], hole_values=[1.5],
        ref_value=None, z_range=None,
    )

    class _Evt:
        inaxes = canvas.axes
        xdata = 0.0
        ydata = 0.0

    # Should not raise and should resolve the measured-hole tooltip text.
    canvas._on_motion(_Evt())
    assert canvas._last_hover == "x=0, y=0\ng RMS=1.5000"

    class _OutEvt:
        inaxes = None
        xdata = None
        ydata = None

    canvas._on_motion(_OutEvt())
    assert canvas._last_hover is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/desktop/test_heatmap_canvas.py::test_heatmap_canvas_motion_shows_tooltip -v`
Expected: FAIL — `AttributeError: 'HeatmapCanvas' object has no attribute '_on_motion'`

- [ ] **Step 3: Add Qt imports**

In `src/desktop/plots/heatmap_canvas.py`, change the existing line:

```python
from PySide6.QtCore import Signal
```

to:

```python
from PySide6.QtCore import Signal
from PySide6.QtGui import QCursor
from PySide6.QtWidgets import QToolTip
```

- [ ] **Step 4: Initialize hover state and connect the motion event**

In `HeatmapCanvas.__init__`, after the existing `self.mpl_connect("button_press_event", self._on_click)` line, add:

```python
        self._grid: np.ndarray = np.empty((1, 1))
        self._hole_lookup: dict[tuple[int, int], float] = {}
        self._ref_value: float | None = None
        self._normalized = False
        self._last_hover: str | None = None
        self.mpl_connect("motion_notify_event", self._on_motion)
```

- [ ] **Step 5: Store hover data in `render_grid`**

In `render_grid`, add the following right after the existing line `self._shape = (grid.shape[0], grid.shape[1])`:

```python
        self._grid = grid
        self._hole_lookup = dict(zip(hole_positions, hole_values))
        self._ref_value = ref_value
        self._normalized = normalized
```

- [ ] **Step 6: Implement `_on_motion`**

Add this method to `HeatmapCanvas`, directly after the existing `_on_click` method:

```python
    def _on_motion(self, event) -> None:
        if getattr(event, "inaxes", None) is not self.axes:
            if self._last_hover is not None:
                QToolTip.hideText()
                self._last_hover = None
            return
        text = resolve_hover(
            getattr(event, "xdata", None),
            getattr(event, "ydata", None),
            grid=self._grid,
            hole_lookup=self._hole_lookup,
            ref_value=self._ref_value,
            normalized=self._normalized,
        )
        if text == self._last_hover:
            return
        self._last_hover = text
        if text:
            QToolTip.showText(QCursor.pos(), text, self)
        else:
            QToolTip.hideText()
```

- [ ] **Step 7: Run the new test and the full canvas test file**

Run: `python3 -m pytest tests/desktop/test_heatmap_canvas.py -v`
Expected: PASS (all tests, including the existing render/click tests)

- [ ] **Step 8: Run the full desktop suite for regressions**

Run: `python3 -m pytest tests/desktop -q`
Expected: PASS (all)

- [ ] **Step 9: Commit**

```bash
git add src/desktop/plots/heatmap_canvas.py tests/desktop/test_heatmap_canvas.py
git commit -m "feat: show hover tooltips on the desktop heatmap"
```

---

### Task 4: Manual verification in the running app

**Files:** none (manual check)

- [ ] **Step 1: Launch the app**

Run: `python3 desktop_main.py`

- [ ] **Step 2: Load a plate and hover over the heatmap**

Verify:
- Over a white measured-point marker → `x=…, y=…` + measured g RMS value.
- Over interpolated area (non-measured cell) → `x=…, y=…` + `Interpoliert (…)` value.
- Over the center/star (when a `reference.csv` is present) → `Referenz (Mitte)` + reference value.
- Over a NaN/gap cell or outside the grid → no tooltip.
- Toggling "Normalisiert" changes the label in the tooltip from `g RMS` to `Normalisiert`.

---

## Notes

- `resolve_hover` is intentionally pure (no Qt/matplotlib event objects) so it is fully unit-testable; the handler only adapts the event and drives `QToolTip`.
- No change to `main_window.py`: `render_grid` already receives `hole_positions`, `hole_values`, `ref_value` and `normalized`.
- `_last_hover` deduplicates so `QToolTip.showText` is only called when the text changes, avoiding churn on every mouse-move event.
