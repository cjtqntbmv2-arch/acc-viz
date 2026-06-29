# Bedienungs-UI-Änderungen Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Sechs Bedienungs-Verbesserungen der Desktop-App: Frequenzband committet erst bei Enter, Histogramm ein-/ausblendbar, RSS-Spektrum zeigt nur die Summenkurve, mehrere Messpunkte überlagert im Spektrum, gewählte Löcher auf der Heatmap markiert, Bins/Statistik ausgegraut bei verstecktem Histogramm.

**Architecture:** Qt-Signal/Slot wie bisher. Auswahl-Zustand (`list[(plate, x, y)]`) lebt in `MainWindow`. `SpectrumCanvas.render_spectrum` wird von „ein Loch" auf „geordnete Punktliste" (`SpectrumPoint`) umgestellt. `HeatmapCanvas` erhält eine Selektions-Marker-Ebene, die inkrementell (ohne Vollneuzeichnung) aktualisiert wird, um das Löschen des Klick-Senders während der Signal-Emission zu vermeiden. Farb-Kopplung Marker↔Linie über den Index in der Auswahlliste (`f"C{i}"`).

**Tech Stack:** Python 3, PySide6 (Qt6), matplotlib, pandas, pytest.

## Global Constraints

- Keine neuen Laufzeit-Abhängigkeiten (PySide6, matplotlib, pandas, numpy, scipy bereits vorhanden).
- Alle nutzersichtbaren Strings über `src/core/strings.py` (`S.*`), deutsch.
- Tests laufen headless (`QT_QPA_PLATFORM=offscreen`, via `tests/desktop/conftest.py`); `qapp`-Fixture verwenden.
- Pyright-CI-Gate muss grün bleiben (keine neuen Typfehler).
- `Settings` ist `@dataclass(frozen=True)`; neue Felder mit Default ans Ende.
- Anzeige-Felder dürfen **nicht** in `_COMPUTE_FIELDS` (sonst teures Neuladen/Re-Analyze).
- Versionsabschluss: MINOR-Bump auf **0.7.0** (pyproject.toml, README-Badge, uv.lock, Tag `v0.7.0`).

---

### Task 1: Frequenzband committet erst bei Enter/Fokuswechsel

**Files:**
- Modify: `src/desktop/control_panel.py:85-94`
- Test: `tests/desktop/test_control_panel.py`

**Interfaces:**
- Consumes: bestehende `_f_min`/`_f_max` `QSpinBox`.
- Produces: keine neuen Signaturen; Verhaltensänderung (kein Emit pro Tastenanschlag).

- [ ] **Step 1: Write the failing test**

In `tests/desktop/test_control_panel.py` ergänzen:

```python
def test_frequency_spinboxes_commit_on_enter_not_per_keystroke(qapp):
    panel = ControlPanel()
    # keyboardTracking aus => valueChanged feuert erst bei Enter/Fokusverlust,
    # nicht ab der ersten getippten Ziffer.
    assert panel._f_min.keyboardTracking() is False
    assert panel._f_max.keyboardTracking() is False
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/desktop/test_control_panel.py::test_frequency_spinboxes_commit_on_enter_not_per_keystroke -v`
Expected: FAIL (`assert True is False`, keyboardTracking standardmäßig True)

- [ ] **Step 3: Write minimal implementation**

In `src/desktop/control_panel.py`, direkt nach `self._f_min = QSpinBox()` … `self._f_max = QSpinBox()`-Setup (innerhalb des `--- frequency band ---`-Blocks, vor den `valueChanged.connect`-Zeilen) ergänzen:

```python
        self._f_min.setKeyboardTracking(False)
        self._f_max.setKeyboardTracking(False)
```

Konkret wird der Block zu:

```python
        # --- frequency band ---
        self._f_min = QSpinBox()
        self._f_min.setRange(0, 25000)
        self._f_min.setSingleStep(100)
        self._f_min.setValue(0)
        self._f_max = QSpinBox()
        self._f_max.setRange(0, 25000)
        self._f_max.setSingleStep(100)
        self._f_max.setValue(25000)
        # Erst bei Enter / Fokusverlust / Step-Pfeil rechnen, nicht pro Tastenanschlag.
        self._f_min.setKeyboardTracking(False)
        self._f_max.setKeyboardTracking(False)
        self._f_min.valueChanged.connect(self._on_f_min_changed)
        self._f_max.valueChanged.connect(self._on_f_max_changed)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/desktop/test_control_panel.py::test_frequency_spinboxes_commit_on_enter_not_per_keystroke -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/desktop/control_panel.py tests/desktop/test_control_panel.py
git commit -m "feat(desktop): frequency band commits on enter, not per keystroke"
```

---

### Task 2: Checkbox „Histogramm anzeigen" + Bins/Statistik ausgrauen

**Files:**
- Modify: `src/core/settings.py:48-59` (neues Feld), `src/core/strings.py` (neue Strings), `src/desktop/control_panel.py` (Checkbox, Slot, Snapshot)
- Test: `tests/desktop/test_control_panel.py`, `tests/core/test_settings.py`

**Interfaces:**
- Produces: `Settings.show_histogram: bool` (Default `True`); `ControlPanel._show_histogram` QCheckBox; `current_settings().show_histogram`.

- [ ] **Step 1: Write the failing test**

In `tests/desktop/test_control_panel.py` ergänzen:

```python
def test_show_histogram_default_true(qapp):
    panel = ControlPanel()
    assert panel.current_settings().show_histogram is True


def test_show_histogram_toggle_reflected_in_settings(qapp):
    panel = ControlPanel()
    panel._show_histogram.setChecked(False)
    assert panel.current_settings().show_histogram is False


def test_hiding_histogram_disables_bins_and_stats(qapp):
    panel = ControlPanel()
    panel._show_histogram.setChecked(False)
    assert panel._bins.isEnabled() is False
    assert panel._histogram_stats.isEnabled() is False
    panel._show_histogram.setChecked(True)
    assert panel._bins.isEnabled() is True
    assert panel._histogram_stats.isEnabled() is True
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/desktop/test_control_panel.py -k "show_histogram or hiding_histogram" -v`
Expected: FAIL (`AttributeError: 'ControlPanel' object has no attribute '_show_histogram'`)

- [ ] **Step 3: Write minimal implementation**

**3a.** In `src/core/settings.py` das Feld ans Ende der Dataclass (nach `interp_method`) ergänzen und im Docstring vermerken:

```python
    interp_method: InterpolationMethod = "linear"
    show_histogram: bool = True
```

Im Klassen-Docstring bei den Attributen ergänzen:

```python
        show_histogram: Whether to show the per-plate histogram below each
            heatmap. Pure display flag — does not affect the computed analysis.
```

**3b.** In `src/core/strings.py` nach `HISTOGRAM_STATS` ergänzen:

```python
SHOW_HISTOGRAM = "Histogramm anzeigen"
```

und bei den Hilfetexten (nach `HELP_HISTOGRAM_STATS`):

```python
HELP_SHOW_HISTOGRAM = (
    "Blendet das Histogramm unter jeder Heatmap ein oder aus. "
    "Reine Anzeige — ändert die Berechnung nicht."
)
```

**3c.** In `src/desktop/control_panel.py` die Checkbox einführen. Vor dem `--- histogram bins ---`-Block einfügen:

```python
        # --- histogram visibility ---
        self._show_histogram = QCheckBox(S.SHOW_HISTOGRAM)
        self._show_histogram.setChecked(True)
        self._show_histogram.setToolTip(S.HELP_SHOW_HISTOGRAM)
        self._show_histogram.toggled.connect(self._on_show_histogram_toggled)
        root.addWidget(self._show_histogram)
```

Neuen Slot bei den anderen `_on_*`-Slots (z. B. nach `_on_interpolate_toggled`) ergänzen:

```python
    def _on_show_histogram_toggled(self, checked: bool) -> None:
        # Bins/Statistik sind sinnlos, wenn das Histogramm aus ist — ausgrauen.
        self._bins.setEnabled(checked)
        self._histogram_stats.setEnabled(checked)
        self.settingsChanged.emit()
```

In `current_settings()` das Feld an den `Settings(...)`-Aufruf anhängen:

```python
            interp_method=interp_method,
            show_histogram=self._show_histogram.isChecked(),
        )
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/desktop/test_control_panel.py -k "show_histogram or hiding_histogram" tests/core/test_settings.py -v`
Expected: PASS (alle)

- [ ] **Step 5: Commit**

```bash
git add src/core/settings.py src/core/strings.py src/desktop/control_panel.py tests/desktop/test_control_panel.py
git commit -m "feat(desktop): add 'show histogram' checkbox, disable bins/stats when hidden"
```

---

### Task 3: MainWindow blendet Histogramm gemäß `show_histogram` aus

**Files:**
- Modify: `src/desktop/main_window.py:279-288` (`_build_plate_column`)
- Test: `tests/desktop/test_main_window.py`

**Interfaces:**
- Consumes: `Settings.show_histogram` (Task 2).

- [ ] **Step 1: Write the failing test**

In `tests/desktop/test_main_window.py` ergänzen:

```python
def test_histogram_hidden_when_show_histogram_false(qapp, tmp_path):
    from src.desktop.plots.histogram_canvas import HistogramCanvas
    from tests.core.conftest import make_plate_folder

    folder = make_plate_folder(tmp_path / "p1", {(0, 0): 1e-3, (1, 1): 4e-3})
    win = MainWindow()
    win.control_panel._show_histogram.setChecked(False)  # triggers settingsChanged
    win.control_panel.set_folder(0, str(folder))          # triggers _refresh + render
    content = win._content_scroll.widget()
    assert content is not None  # pyright: widget() is QWidget | None
    histograms = content.findChildren(HistogramCanvas)
    assert histograms == []


def test_histogram_shown_by_default(qapp, tmp_path):
    from src.desktop.plots.histogram_canvas import HistogramCanvas
    from tests.core.conftest import make_plate_folder

    folder = make_plate_folder(tmp_path / "p1", {(0, 0): 1e-3, (1, 1): 4e-3})
    win = MainWindow()
    win.control_panel.set_folder(0, str(folder))
    content = win._content_scroll.widget()
    assert content is not None  # pyright: widget() is QWidget | None
    assert len(content.findChildren(HistogramCanvas)) >= 1
```

> **Abhängigkeit:** Task 2 muss gemerged sein (`_show_histogram` + `settingsChanged`-Verdrahtung), sonst schlägt Step 2 mit `AttributeError` fehl statt aus dem richtigen Grund (Histogramm noch vorhanden).

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/desktop/test_main_window.py::test_histogram_hidden_when_show_histogram_false -v`
Expected: FAIL (Histogramm wird immer gebaut → Liste nicht leer)

- [ ] **Step 3: Write minimal implementation**

In `src/desktop/main_window.py`, `_build_plate_column`, den Histogramm-Block in eine Bedingung setzen:

```python
        if settings.show_histogram:
            histogram = HistogramCanvas()
            histogram.render_values(
                sparse_grid.ravel(),
                bins=settings.histogram_bins,
                normalized=settings.normalize,
                ref_value=marker,
                x_range=analysis.hist_range if settings.shared_scale else None,
                show_stats=settings.histogram_stats,
            )
            layout.addWidget(histogram, stretch=2)

        return column
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/desktop/test_main_window.py -k histogram -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/desktop/main_window.py tests/desktop/test_main_window.py
git commit -m "feat(desktop): hide per-plate histogram when show_histogram is off"
```

---

### Task 4: SpectrumCanvas auf Punktliste umstellen (RSS nur Summe, Ref nur bei Einzelauswahl)

**Files:**
- Modify: `src/desktop/plots/spectrum_canvas.py` (kompletter Render-Pfad), `src/core/strings.py` (neue Strings, ungenutzte entfernen)
- Test: `tests/desktop/test_plot_canvases.py` (bestehende Spektrum-Tests anpassen + neue)

**Interfaces:**
- Produces:
  - `SpectrumPoint(plate_name: str, x_hole: int, y_hole: int, hole_df: pd.DataFrame, ref_df: pd.DataFrame | None, color: str | None = None)` (frozen dataclass, exportiert aus `spectrum_canvas.py`).
  - `SpectrumCanvas.render_spectrum(points: list[SpectrumPoint], *, axis: Axis, f_min: int, f_max: int) -> None`.
- Regeln: RSS zeichnet pro Punkt **eine** Summenkurve (keine X/Y/Z-Linien). Referenz-Linie nur, wenn `len(points) == 1`.

- [ ] **Step 1: Write the failing tests**

In `tests/desktop/test_plot_canvases.py` den Import ergänzen und die Spektrum-Tests ersetzen. Import oben:

```python
from src.desktop.plots.spectrum_canvas import SpectrumCanvas, SpectrumPoint
```

Helfer `_df()` bleibt. Die bestehenden Spektrum-Tests (`test_spectrum_single_axis_one_line_without_ref`, `_two_lines_with_ref`, `_rss_has_three_axes_plus_sum`, `_rss_with_ref_adds_ref_sum_line`, `_uses_log_y_axis`) durch folgende ersetzen:

```python
def _point(ref=None, color=None):
    return SpectrumPoint(
        plate_name="Platte 1", x_hole=0, y_hole=0,
        hole_df=_df(), ref_df=ref, color=color,
    )


def test_spectrum_single_axis_one_line_without_ref(qapp):
    canvas = SpectrumCanvas()
    canvas.render_spectrum([_point()], axis="X", f_min=0, f_max=2)
    assert len(canvas.axes.get_lines()) == 1


def test_spectrum_single_axis_two_lines_with_ref(qapp):
    canvas = SpectrumCanvas()
    canvas.render_spectrum([_point(ref=_df())], axis="X", f_min=0, f_max=2)
    assert len(canvas.axes.get_lines()) == 2  # hole + ref


def test_spectrum_rss_single_point_only_sum_line(qapp):
    canvas = SpectrumCanvas()
    canvas.render_spectrum([_point()], axis="RSS", f_min=0, f_max=2)
    # Nur die RSS-Summenkurve, keine X/Y/Z-Einzellinien mehr.
    assert len(canvas.axes.get_lines()) == 1


def test_spectrum_rss_single_point_with_ref_adds_ref_sum(qapp):
    canvas = SpectrumCanvas()
    canvas.render_spectrum([_point(ref=_df())], axis="RSS", f_min=0, f_max=2)
    assert len(canvas.axes.get_lines()) == 2  # sum + ref-sum


def test_spectrum_multiple_points_one_line_each_no_ref(qapp):
    canvas = SpectrumCanvas()
    p0 = SpectrumPoint("Platte 1", 0, 0, _df(), _df(), "C0")
    p1 = SpectrumPoint("Platte 2", 1, 1, _df(), _df(), "C1")
    canvas.render_spectrum([p0, p1], axis="X", f_min=0, f_max=2)
    # Zwei Punkte => zwei Linien, Referenz bei Mehrfachauswahl unterdrückt.
    assert len(canvas.axes.get_lines()) == 2


def test_spectrum_uses_log_y_axis(qapp):
    canvas = SpectrumCanvas()
    canvas.render_spectrum([_point()], axis="X", f_min=0, f_max=2)
    assert canvas.axes.get_yscale() == "log"


def test_spectrum_empty_points_does_not_raise(qapp):
    canvas = SpectrumCanvas()
    canvas.render_spectrum([], axis="X", f_min=0, f_max=2)
    assert len(canvas.axes.get_lines()) == 0
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/desktop/test_plot_canvases.py -k spectrum -v`
Expected: FAIL (`ImportError: cannot import name 'SpectrumPoint'` bzw. Signatur-Mismatch)

- [ ] **Step 3: Write minimal implementation**

`src/desktop/plots/spectrum_canvas.py` komplett ersetzen:

```python
from __future__ import annotations

"""Native matplotlib PSD spectrum canvas for the application.

A log-scaled PSD plot. Each selected hole is drawn as one line in a shared
plot; ``"RSS"`` draws one summed line per hole (no per-axis lines). The
optional dashed reference line is shown only when exactly one hole is selected.
"""

from dataclasses import dataclass
from typing import Literal

import pandas as pd
from matplotlib.figure import Figure

from src.analysis.rms import rss_series
from src.core.settings import Axis
from src.desktop.plots._canvas_base import ScrollPassthroughCanvas
from src.core import strings as S

_FLOOR = 1e-30

# Floor height (px) so the plot keeps a readable size and the enclosing
# QScrollArea scrolls instead of squeezing the canvas.
_MIN_HEIGHT_PX = 300


@dataclass(frozen=True)
class SpectrumPoint:
    """One selected hole to draw in the spectrum.

    Attributes:
        plate_name: Plate the hole belongs to (shown in the legend).
        x_hole, y_hole: Hole coordinates.
        hole_df: The hole's PSD frame (columns ``Frequenz_Hz``, ``PSD_{X,Y,Z}_g2Hz``).
        ref_df: The plate's reference PSD frame, or ``None``.
        color: Explicit line color (``"C0"`` …) coupling the line to its heatmap
            marker; ``None`` lets matplotlib pick from its cycle.
    """

    plate_name: str
    x_hole: int
    y_hole: int
    hole_df: pd.DataFrame
    ref_df: pd.DataFrame | None
    color: str | None = None


def _rss_sum(df: pd.DataFrame) -> pd.Series:
    """Per-frequency sum of the three axis PSDs, floored for the log y-axis."""
    return rss_series(df).clip(lower=_FLOOR)


class SpectrumCanvas(ScrollPassthroughCanvas):
    """A matplotlib PSD spectrum plot for one or more selected holes."""

    def __init__(self) -> None:
        self._figure = Figure(figsize=(6, 3), layout="constrained")
        super().__init__(self._figure)
        self.axes = self._figure.add_subplot(111)
        self.setMinimumHeight(_MIN_HEIGHT_PX)

    def render_spectrum(
        self,
        points: list[SpectrumPoint],
        *,
        axis: Axis,
        f_min: int,
        f_max: int,
    ) -> None:
        """Draw the spectrum for the given selected holes."""
        self._figure.clear()
        self.axes = self._figure.add_subplot(111)

        show_ref = len(points) == 1
        for p in points:
            if axis == "RSS":
                self._add_rss_line(p, show_ref)
            else:
                self._add_single_axis_line(p, axis, show_ref)

        y_label = (
            S.SPECTRUM_Y_LABEL_RSS if axis == "RSS"
            else S.SPECTRUM_Y_LABEL_TMPL.format(axis=axis)
        )
        self.axes.axvspan(f_min, f_max, facecolor="yellow", alpha=0.1, linewidth=0)
        self.axes.set_yscale("log")
        self.axes.set_xlabel(S.SPECTRUM_X_LABEL)
        self.axes.set_ylabel(y_label)
        self.axes.set_title(self._title(points, axis))
        if points:
            self.axes.legend(loc="upper right", fontsize="small")
        self.draw_idle()

    @staticmethod
    def _title(points: list[SpectrumPoint], axis: Axis) -> str:
        if len(points) == 1:
            p = points[0]
            return S.SPECTRUM_TITLE.format(
                name=p.plate_name, x=p.x_hole, y=p.y_hole, axis=axis
            )
        return S.SPECTRUM_TITLE_MULTI.format(axis=axis, n=len(points))

    def _add_single_axis_line(
        self, p: SpectrumPoint, axis: Literal["X", "Y", "Z"], show_ref: bool
    ) -> None:
        col_psd = f"PSD_{axis}_g2Hz"
        y_series = p.hole_df[col_psd].clip(lower=_FLOOR)
        self.axes.plot(
            p.hole_df["Frequenz_Hz"], y_series,
            linewidth=1.5, color=p.color,
            label=S.SPECTRUM_TRACE_POINT_TMPL.format(
                plate=p.plate_name, x=p.x_hole, y=p.y_hole
            ),
        )
        if show_ref and p.ref_df is not None:
            y_ref = p.ref_df[col_psd].clip(lower=_FLOOR)
            self.axes.plot(
                p.ref_df["Frequenz_Hz"], y_ref,
                color="grey", linewidth=1, linestyle="--",
                label=S.SPECTRUM_TRACE_REF,
            )

    def _add_rss_line(self, p: SpectrumPoint, show_ref: bool) -> None:
        self.axes.plot(
            p.hole_df["Frequenz_Hz"], _rss_sum(p.hole_df),
            linewidth=2.0, color=p.color,
            label=S.SPECTRUM_TRACE_POINT_TMPL.format(
                plate=p.plate_name, x=p.x_hole, y=p.y_hole
            ),
        )
        if show_ref and p.ref_df is not None:
            self.axes.plot(
                p.ref_df["Frequenz_Hz"], _rss_sum(p.ref_df),
                color="grey", linewidth=1.2, linestyle="--",
                label=S.SPECTRUM_TRACE_REF,
            )
```

In `src/core/strings.py`: neue Strings ergänzen und die nun ungenutzten entfernen.

Ergänzen (nach `SPECTRUM_TRACE_AXIS_TMPL`-Zeile bzw. im Spektrum-Block):

```python
SPECTRUM_TRACE_POINT_TMPL = "{plate} — ({x}, {y})"
SPECTRUM_TITLE_MULTI = "Spektrum · Achse {axis} · {n} Bohrungen"
```

Entfernen (nicht mehr referenziert — vor dem Entfernen mit
`grep -rn "SPECTRUM_TRACE_SUM\|SPECTRUM_TRACE_AXIS_TMPL\|SPECTRUM_TRACE_HOLE" src tests`
prüfen; `SPECTRUM_TRACE_HOLE` wird nach diesem Task ebenfalls nicht mehr verwendet):

```python
SPECTRUM_TRACE_HOLE = "Bohrung ({x}, {y})"
SPECTRUM_TRACE_SUM = "Summe X+Y+Z"
SPECTRUM_TRACE_AXIS_TMPL = "PSD {axis}"
```

- [ ] **Step 4: MainWindow auf die neue Signatur heben (minimal, Einzelpunkt)**

`MainWindow._on_hole_clicked` ruft sonst noch die alte `render_spectrum`-Signatur
auf → der pyright-Gate (Global Constraint) würde auf diesem Commit rot. Daher
hier schon den Aufruf auf die neue Punktlisten-Signatur umstellen — verhaltens-
erhaltend (weiterhin genau ein Loch). Die volle Mehrfachauswahl folgt in Task 6.

In `src/desktop/main_window.py` den Import erweitern:

```python
from src.desktop.plots.spectrum_canvas import SpectrumCanvas, SpectrumPoint
```

und in `_on_hole_clicked` den `canvas.render_spectrum(...)`-Block ersetzen:

```python
        canvas = SpectrumCanvas()
        canvas.render_spectrum(
            [SpectrumPoint(
                plate_name=name, x_hole=x_hole, y_hole=y_hole,
                hole_df=hole_data[(x_hole, y_hole)], ref_df=ref_df,
            )],
            axis=self._settings.axis,
            f_min=self._settings.f_min,
            f_max=self._settings.f_max,
        )
        self._set_spectrum_canvas(canvas)
```

- [ ] **Step 5: Run tests + pyright to verify green**

Run: `pytest tests/desktop/test_plot_canvases.py -k spectrum -v && pytest tests/desktop/test_main_window.py -q && pyright src tests`
Expected: PASS (Spektrum-Tests), main_window weiter grün (kein Test klickt aktuell ein Loch), pyright 0 Fehler.

- [ ] **Step 6: Commit**

```bash
git add src/desktop/plots/spectrum_canvas.py src/core/strings.py src/desktop/main_window.py tests/desktop/test_plot_canvases.py
git commit -m "feat(desktop): spectrum takes point list; RSS shows only sum, ref only for single point"
```

---

### Task 5: HeatmapCanvas — Selektions-Marker

**Files:**
- Modify: `src/desktop/plots/heatmap_canvas.py` (Konstanten, `__init__`, `render_grid`, neue Methoden)
- Test: `tests/desktop/test_heatmap_canvas.py`

**Interfaces:**
- Produces:
  - `HeatmapCanvas.render_grid(..., selected: Sequence[tuple[int, int, str]] = ())` — `(x, y, color)` je gewähltem Loch dieser Platte.
  - `HeatmapCanvas.set_selected(self, selected: Sequence[tuple[int, int, str]]) -> None` — aktualisiert nur die Marker-Ebene (sicher aus dem eigenen Klick-Handler heraus aufrufbar, da der Canvas nicht zerstört wird).

> **pyright:** `selected` ist als `Sequence[...]` typisiert (nicht `list[...]`), weil
> der Default `()` (leeres Tuple) sonst `reportArgumentType` auslöst. Konsumenten
> erhalten `list(selected)`/eine echte `list`, also bleibt alles kompatibel.

- [ ] **Step 1: Write the failing test**

In `tests/desktop/test_heatmap_canvas.py` ergänzen. Falls noch kein Helfer zum Rendern existiert, ein minimales Grid bauen (an bestehenden Tests orientieren):

```python
import numpy as np

from src.desktop.plots.heatmap_canvas import HeatmapCanvas


def _render_basic(canvas, selected=()):
    grid = np.array([[1.0, 2.0], [3.0, 4.0]])
    canvas.render_grid(
        grid,
        plate_name="Platte 1",
        title="Platte 1",
        colorscale="Viridis",
        normalized=False,
        hole_positions=[(0, 0), (1, 1)],
        hole_values=[1.0, 4.0],
        ref_value=None,
        z_range=None,
        selected=selected,
    )


def test_render_grid_without_selection_has_no_selection_artist(qapp):
    canvas = HeatmapCanvas()
    _render_basic(canvas)
    assert canvas._selection_artist is None


def test_render_grid_with_selection_draws_marker(qapp):
    canvas = HeatmapCanvas()
    _render_basic(canvas, selected=[(0, 0, "C0")])
    assert canvas._selection_artist is not None


def test_set_selected_updates_marker_layer(qapp):
    canvas = HeatmapCanvas()
    _render_basic(canvas)
    canvas.set_selected([(1, 1, "C1")])
    assert canvas._selection_artist is not None
    # Erneutes Leeren entfernt die Marker-Ebene wieder.
    canvas.set_selected([])
    assert canvas._selection_artist is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/desktop/test_heatmap_canvas.py -k "selection or selected or marker" -v`
Expected: FAIL (`render_grid() got an unexpected keyword argument 'selected'`)

- [ ] **Step 3: Write minimal implementation**

In `src/desktop/plots/heatmap_canvas.py`:

**3a.** Import für den Typ ergänzen (oben in `heatmap_canvas.py`, nach `from __future__ import annotations`) und bei den Marker-Konstanten (neben `HOLE_MARKER_SIZE`) die Größe:

```python
from collections.abc import Sequence
```

```python
SELECTED_MARKER_SIZE = 220
```

**3b.** In `__init__` (am Ende) initialisieren:

```python
        self._selection_artist = None
```

**3c.** `render_grid`-Signatur um `selected` erweitern:

```python
    def render_grid(
        self,
        grid: np.ndarray,
        *,
        plate_name: str,
        title: str,
        colorscale: str,
        normalized: bool,
        hole_positions: list[tuple[int, int]],
        hole_values: list[float],
        ref_value: float | None,
        z_range: tuple[float, float] | None,
        selected: Sequence[tuple[int, int, str]] = (),
    ) -> None:
```

Direkt nach **jedem** `self._figure.clear()` in `render_grid` (es gibt den Empty-Pfad und den Hauptpfad) die Marker-Referenz zurücksetzen, da `clear()` alle Artists verwirft:

```python
        self._figure.clear()
        self._selection_artist = None
```

Am Ende des Hauptpfads (nach dem `ref_value`-Stern, vor `set_title`) die Selektion zeichnen:

```python
        self._draw_selection(list(selected))
```

**3d.** Zwei neue Methoden ergänzen (nach `render_grid`):

```python
    def _draw_selection(self, selected: Sequence[tuple[int, int, str]]) -> None:
        """(Re)draw the selection ring layer; removes the previous one first."""
        if self._selection_artist is not None:
            self._selection_artist.remove()
            self._selection_artist = None
        if selected:
            xs = [x for (x, _, _) in selected]
            ys = [y for (_, y, _) in selected]
            colors = [c for (_, _, c) in selected]
            self._selection_artist = self.axes.scatter(
                xs, ys,
                s=SELECTED_MARKER_SIZE,
                facecolors="none",
                edgecolors=colors,
                linewidths=2.5,
                zorder=5,
            )

    def set_selected(self, selected: Sequence[tuple[int, int, str]]) -> None:
        """Update only the selection marker layer and redraw.

        Safe to call from within this canvas' own click handler — it never
        destroys the canvas, and ``draw_idle`` defers the actual paint.
        """
        self._draw_selection(selected)
        self.draw_idle()
```

- [ ] **Step 4: Run tests + pyright to verify they pass**

Run: `pytest tests/desktop/test_heatmap_canvas.py -v && pyright src/desktop/plots/heatmap_canvas.py`
Expected: PASS (neue + bestehende); pyright 0 Fehler (Default `()` ist dank `Sequence`-Typ gültig).

- [ ] **Step 5: Commit**

```bash
git add src/desktop/plots/heatmap_canvas.py tests/desktop/test_heatmap_canvas.py
git commit -m "feat(desktop): heatmap selection-marker layer (render_grid selected= + set_selected)"
```

---

### Task 6: MainWindow — Mehrfachauswahl verdrahten

**Files:**
- Modify: `src/desktop/main_window.py` (Imports, Auswahl-Zustand, `_on_hole_clicked`, `_set_spectrum_canvas`/Spektrum-Helfer, `_render`, `_build_plate_column`, `_reset_state`, Ordnerwechsel)
- Test: `tests/desktop/test_main_window.py`

**Interfaces:**
- Consumes: `SpectrumPoint`/`render_spectrum(points, ...)` (Task 4), `HeatmapCanvas.render_grid(selected=...)` & `set_selected` (Task 5).
- Produces: `MainWindow._selected_points: list[tuple[str, int, int]]`; Slots/Helfer `_on_hole_clicked`, `_selected_for_plate`, `_draw_spectrum_from_selection`, `_color_for_index`.

- [ ] **Step 1: Write the failing tests**

In `tests/desktop/test_main_window.py` ergänzen:

```python
def _click(win, name, x, y, *, ctrl=False):
    """Simulate a hole click with optional Ctrl modifier via the QApplication seam."""
    from PySide6.QtCore import Qt
    from PySide6.QtWidgets import QApplication

    mods = (
        Qt.KeyboardModifier.ControlModifier if ctrl
        else Qt.KeyboardModifier.NoModifier
    )
    orig = QApplication.keyboardModifiers
    QApplication.keyboardModifiers = staticmethod(lambda: mods)
    try:
        win._on_hole_clicked(name, x, y)
    finally:
        QApplication.keyboardModifiers = orig


def test_plain_click_selects_single_point(qapp, tmp_path):
    from tests.core.conftest import make_plate_folder

    folder = make_plate_folder(tmp_path / "p1", {(0, 0): 1e-3, (1, 1): 4e-3})
    win = MainWindow()
    win.control_panel.set_folder(0, str(folder))
    _click(win, "Platte 1", 0, 0)
    assert win._selected_points == [("Platte 1", 0, 0)]
    _click(win, "Platte 1", 1, 1)  # plain click replaces
    assert win._selected_points == [("Platte 1", 1, 1)]


def test_ctrl_click_accumulates_and_toggles(qapp, tmp_path):
    from tests.core.conftest import make_plate_folder

    folder = make_plate_folder(tmp_path / "p1", {(0, 0): 1e-3, (1, 1): 4e-3})
    win = MainWindow()
    win.control_panel.set_folder(0, str(folder))
    _click(win, "Platte 1", 0, 0)
    _click(win, "Platte 1", 1, 1, ctrl=True)
    assert win._selected_points == [("Platte 1", 0, 0), ("Platte 1", 1, 1)]
    _click(win, "Platte 1", 0, 0, ctrl=True)  # toggle off
    assert win._selected_points == [("Platte 1", 1, 1)]


def test_selection_survives_settings_change(qapp, tmp_path):
    from tests.core.conftest import make_plate_folder

    folder = make_plate_folder(tmp_path / "p1", {(0, 0): 1e-3, (1, 1): 4e-3})
    win = MainWindow()
    win.control_panel.set_folder(0, str(folder))
    _click(win, "Platte 1", 0, 0)
    win.control_panel.set_axis("RSS")  # triggers _refresh -> _render
    assert win._selected_points == [("Platte 1", 0, 0)]
    # Spektrum muss nach dem Re-Render real neu gezeichnet sein (nicht nur != None):
    # RSS + Einzelpunkt, ref_df None => genau eine Summenlinie.
    assert win._spectrum_canvas is not None
    assert len(win._spectrum_canvas.axes.get_lines()) >= 1


def test_folder_change_clears_selection(qapp, tmp_path):
    from tests.core.conftest import make_plate_folder

    folder1 = make_plate_folder(tmp_path / "p1", {(0, 0): 1e-3, (1, 1): 4e-3})
    folder2 = make_plate_folder(tmp_path / "p2", {(0, 0): 2e-3, (1, 1): 5e-3})
    win = MainWindow()
    win.control_panel.set_folder(0, str(folder1))
    _click(win, "Platte 1", 0, 0)
    win.control_panel.set_folder(0, str(folder2))  # new folder -> reload
    assert win._selected_points == []
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/desktop/test_main_window.py -k "click or selection or folder_change" -v`
Expected: FAIL (`AttributeError: ... '_selected_points'` / Signatur-Mismatch)

- [ ] **Step 3: Write minimal implementation**

In `src/desktop/main_window.py`:

**3a.** Import sicherstellen (bereits in Task 4/Step 4 ergänzt — prüfen, sonst nachziehen):

```python
from src.desktop.plots.spectrum_canvas import SpectrumCanvas, SpectrumPoint
```

**3b.** In `__init__`, bei den Auswahl-/State-Feldern ergänzen:

```python
        self._selected_points: list[tuple[str, int, int]] = []
```

**3c.** In `_reset_state` die Auswahl mitleeren:

```python
        self._spectrum_canvas = None
        self._spectrum_layout = None
        self._selected_points = []
        self._export_action.setEnabled(False)
```

**3d.** In `_refresh`, im `folders_changed`-Erfolgszweig (nach erfolgreichem Reload, vor `self._render`) die Auswahl leeren — andere Platten machen alte Punkte ungültig. Direkt nach `self._last_good_folder_texts = self._control_panel.folder_texts()`:

```python
            self._last_good_folder_texts = self._control_panel.folder_texts()
            self._selected_points = []
            load = loaded
```

**3e.** Farb-Helfer und Per-Platte-Filter ergänzen (z. B. nach `_reset_state`):

```python
    @staticmethod
    def _color_for_index(i: int) -> str:
        # matplotlib-Default-Zyklus; koppelt Spektrum-Linie und Heatmap-Marker.
        return f"C{i % 10}"

    def _selected_for_plate(self, name: str) -> list[tuple[int, int, str]]:
        return [
            (x, y, self._color_for_index(i))
            for i, (p, x, y) in enumerate(self._selected_points)
            if p == name
        ]
```

**3f.** In `_build_plate_column` den `render_grid`-Aufruf um `selected=` erweitern:

```python
        heatmap.render_grid(
            analysis.interp_grids[name],
            plate_name=name,
            title=name,
            colorscale=settings.colorscale,
            normalized=settings.normalize,
            hole_positions=positions,
            hole_values=values,
            ref_value=marker,
            z_range=analysis.z_range,
            selected=self._selected_for_plate(name),
        )
```

**3g.** Am Ende von `_render` (nach `self._content_scroll.setWidget(content)`) das Spektrum aus der Auswahl wiederherstellen (Persistenz):

```python
        self._content_scroll.setWidget(content)
        if self._selected_points:
            self._draw_spectrum_from_selection()
```

**3h.** `_on_hole_clicked` ersetzen:

```python
    def _on_hole_clicked(self, name: str, x_hole: int, y_hole: int) -> None:
        """Update the selected-hole set and redraw spectrum + heatmap markers.

        Plain click replaces the selection; Ctrl/Cmd+click toggles a point
        (Qt maps Cmd to ControlModifier on macOS).
        """
        from PySide6.QtWidgets import QApplication

        if self._load is None or self._settings is None:
            return
        entry = self._load.plates.get(name)
        if entry is None:
            return
        hole_data, _ref_df = entry
        point = (name, x_hole, y_hole)
        additive = bool(
            QApplication.keyboardModifiers() & Qt.KeyboardModifier.ControlModifier
        )

        if additive and point in self._selected_points:
            self._selected_points.remove(point)  # toggle off — no data check needed
        else:
            if (x_hole, y_hole) not in hole_data:
                # Klick auf leere/Gap-Zelle: bestehende Auswahl bewusst NICHT
                # verwerfen (Fehlklick soll eine gute Auswahl nicht zerstören).
                self.statusBar().showMessage(
                    S.WARN_NO_DATA_FOR_HOLE.format(name=name, x=x_hole, y=y_hole), 8000
                )
                return
            if additive:
                self._selected_points.append(point)
            else:
                self._selected_points = [point]

        # Marker auf allen Heatmaps aktualisieren (Farb-Indices verschieben sich
        # beim Entfernen) — inkrementell, ohne den Klick-Sender zu zerstören.
        for plate_name, heatmap in self._heatmaps.items():
            heatmap.set_selected(self._selected_for_plate(plate_name))
        self._draw_spectrum_from_selection()
```

**3i.** Neuen Spektrum-Helfer ergänzen und die alte Direkt-Rendering-Logik ersetzen:

```python
    def _draw_spectrum_from_selection(self) -> None:
        """Render all selected holes overlaid into one spectrum canvas."""
        if self._spectrum_layout is None or self._load is None or self._settings is None:
            return
        if not self._selected_points:
            self._clear_spectrum()
            return
        points: list[SpectrumPoint] = []
        for i, (name, x, y) in enumerate(self._selected_points):
            entry = self._load.plates.get(name)
            if entry is None:
                continue
            hole_data, ref_df = entry
            if (x, y) not in hole_data:
                continue
            points.append(
                SpectrumPoint(
                    plate_name=name, x_hole=x, y_hole=y,
                    hole_df=hole_data[(x, y)], ref_df=ref_df,
                    color=self._color_for_index(i),
                )
            )
        if not points:
            self._clear_spectrum()
            return
        canvas = SpectrumCanvas()
        canvas.render_spectrum(
            points,
            axis=self._settings.axis,
            f_min=self._settings.f_min,
            f_max=self._settings.f_max,
        )
        self._set_spectrum_canvas(canvas)

    def _clear_spectrum(self) -> None:
        """Drop any spectrum content (e.g. when the selection becomes empty)."""
        if self._spectrum_layout is None:
            return
        while self._spectrum_layout.count():
            item = self._spectrum_layout.takeAt(0)
            if item is None:
                break
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()
        self._spectrum_canvas = None
```

**3j.** `_set_spectrum_canvas` auf `_clear_spectrum` umstellen (DRY — die Clear-Schleife nicht duplizieren):

```python
    def _set_spectrum_canvas(self, canvas: SpectrumCanvas) -> None:
        self._clear_spectrum()
        if self._spectrum_layout is None:
            return
        self._spectrum_layout.addWidget(canvas)
        self._spectrum_canvas = canvas
```

> Hinweis: `_clear_spectrum` leert das gesamte `_spectrum_layout` inkl. des
> `hint`-Labels — wie bisher beim ersten Spektrum-Draw. Beim Abwählen des letzten
> Punkts bleibt die Spektrumsfläche daher leer (kein Hint). Das ist kein Regress
> (Spec verlangt keinen Hint-Restore) und Plain-Click setzt die Auswahl ohnehin
> wieder auf einen Punkt.

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/desktop/test_main_window.py -v`
Expected: PASS

Dann die **gesamte** Suite:

Run: `pytest -q`
Expected: PASS (alle). Bei rotem Pyright-Lauf: `pyright src tests` prüfen.

- [ ] **Step 5: Commit**

```bash
git add src/desktop/main_window.py tests/desktop/test_main_window.py
git commit -m "feat(desktop): multi-point spectrum selection with coupled heatmap markers"
```

---

### Task 7: Versions-Bump auf 0.7.0

**Files:**
- Modify: `pyproject.toml`, `README.md` (Badge), `uv.lock`
- Verify: App-/CLI-Versionsausgabe falls vorhanden

**Interfaces:** keine Code-Schnittstellen.

- [ ] **Step 1: Konsistenz prüfen**

Run: `grep -n "0.6.0" pyproject.toml README.md; git tag -l v0.7.0`
Expected: aktuelle Stellen zeigen `0.6.0`; kein Tag `v0.7.0` vorhanden.

- [ ] **Step 2: Version anheben**

`pyproject.toml`: `version = "0.6.0"` → `version = "0.7.0"`.
`README.md`-Badge: `version-0.6.0-blue` → `version-0.7.0-blue`.

- [ ] **Step 3: Lockfile synchronisieren**

Run: `uv lock`
Expected: `uv.lock` aktualisiert die Projektversion auf 0.7.0.

- [ ] **Step 4: Tests + Konsistenz final**

Run: `pytest -q && grep -rn "0.7.0" pyproject.toml README.md uv.lock | head`
Expected: Tests grün; alle drei Stellen zeigen 0.7.0.

- [ ] **Step 5: Commit + Tag + Push**

```bash
git add pyproject.toml README.md uv.lock
git commit -m "chore: bump version to 0.7.0"
git tag -a v0.7.0 -m "v0.7.0"
git push --follow-tags
```

---

## Self-Review (vom Plan-Autor durchgeführt)

**Spec-Abdeckung:**
- #1 Frequenzband-Commit → Task 1 ✓
- #2 Histogramm-Checkbox → Task 2 (Panel/Settings) + Task 3 (Render) ✓
- #3 RSS nur Summe → Task 4 ✓
- #4 Mehrfach-Messpunkte überlagert/persistent → Task 4 (Canvas) + Task 6 (Wiring) ✓
- #5 Heatmap-Marker → Task 5 (Canvas) + Task 6 (Farb-Kopplung/Update) ✓
- #6 Bins/Statistik ausgrauen → Task 2 ✓
- Versionierung → Task 7 ✓

**Platzhalter-Scan:** Keine TBD/TODO; alle Code-Schritte vollständig.

**Typ-Konsistenz:** `SpectrumPoint`-Felder identisch in Task 4 (Definition) und Task 6 (Konstruktion). `render_grid(selected=...)`/`set_selected(...)`/`_draw_selection(...)` nutzen einheitlich `Sequence[tuple[int,int,str]]` (Task 5), gespeist mit echten `list`s aus `_selected_for_plate` (Task 6). `render_spectrum(points, *, axis, f_min, f_max)` identisch in Task 4 (inkl. minimalem main_window-Aufruf) und Task-6-Aufruf. `_selected_points` als `list[tuple[str,int,int]]` durchgängig.

**pyright-Gate:** durchgehend grün gehalten — `selected` als `Sequence` typisiert (kein `list = ()`-Fehler); `_content_scroll.widget()` in Tests mit `assert ... is not None` geguardet; Task 4 hebt `main_window._on_hole_clicked` direkt auf die neue `render_spectrum`-Signatur, sodass kein Zwischen-Commit rot wird.

**Reihenfolge-Hinweis:** Task 4 stellt den Spektrum-Aufruf in `main_window.py` minimal (Einzelpunkt) mit um, sodass Tests **und** pyright nach jedem Task grün bleiben; die volle Mehrfachauswahl folgt in Task 6.

**Adversariale Prüfung (3 Subagenten):** Plan komplett auf eine isolierte Repo-Kopie angewendet → 200 Tests grün; alle Qt/matplotlib-Annahmen verifiziert (keyboardTracking, keyboardModifiers-Monkeypatch + Cmd→Ctrl, `scatter(edgecolors=[...])`, `artist.remove()` nach `figure.clear()`, Delete-während-Signal, `draw_idle` re-entrant, `rss_series`). Die einzigen Funde (3 pyright-Fehler + 1 schwacher Test) sind oben eingearbeitet.
