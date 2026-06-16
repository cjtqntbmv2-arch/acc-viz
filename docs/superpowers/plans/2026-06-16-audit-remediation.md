# Audit-Remediation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Behebe die im Audit vom 2026-06-16 gefundenen Korrektheits-, Konsistenz-, Performance- und UX-Mängel von acc_visualisation in risikogeordneter Reihenfolge (erst absichern, dann aufräumen, dann optimieren).

**Architecture:** Frontend-agnostischer Kern (`src/core`, `src/analysis`, `src/io`) treibt zwei Frontends: Streamlit (`app.py`, Plotly) und PySide6-Desktop (`desktop_main.py`, matplotlib). Fixes landen so weit wie möglich im gemeinsamen Kern bzw. in beiden Frontends synchron, damit die zwei Oberflächen nicht weiter auseinanderlaufen.

**Tech Stack:** Python 3.10+, numpy/scipy/pandas, Streamlit+Plotly, PySide6+matplotlib, pytest, PyInstaller, GitHub Actions.

**Konventionen (bereits im Repo etabliert — einhalten):**
- Tests unter `tests/<bereich>/`, Spiegelung der `src`-Struktur. Plate-Fixtures via `tests.core.conftest.make_plate_folder` und `tests.io.conftest.write_csv`.
- Qt-Tests nutzen die `qapp`-Fixture (Session-scoped, offscreen) aus `tests/desktop/conftest.py`.
- Streamlit-Tests nutzen `streamlit.testing.v1.AppTest` (siehe `tests/ui/test_smoke.py`) und die `smoke_plate_folder`-Fixture aus `tests/ui/conftest.py`.
- Alle Tests headless: `QT_QPA_PLATFORM=offscreen` (in der desktop-conftest gesetzt).
- Voller Lauf: `python -m pytest -q` (Baseline aktuell: 179 passed).
- User-sichtbare Strings ausschließlich in `src/ui/strings.py` (Modul-Alias `S`).

---

## File Structure

**Phase 1 — Stabilisieren**
- Modify: `src/analysis/rms.py` — numpy-`trapezoid`-Kompatibilitäts-Shim.
- Modify: `requirements.txt`, `pyproject.toml` — korrekter numpy-Floor + Runtime-Deps deklarieren.
- Modify: `app.py` — Histogramm bekommt `hist_range` statt `z_range`.
- Modify: `src/ui/heatmap.py` — Empty-State-Annotation bei vollständig leerem Gitter.
- Modify: `src/desktop/plots/heatmap_canvas.py` — Empty-State-Text bei vollständig leerem Gitter.
- Modify: `src/desktop/control_panel.py` — Frequenzband erzwingt `f_max > f_min`.
- Test: `tests/analysis/test_rms.py`, `tests/ui/test_heatmap.py` (neu), `tests/desktop/test_heatmap_canvas.py`, `tests/desktop/test_control_panel.py`, `tests/ui/test_smoke.py`.

**Phase 2 — Absichern**
- Modify: `.github/workflows/ci.yml` — pyright-Step (non-blocking, gepinnt), Python-Matrix 3.10/3.11/3.12.

**Phase 3 — Aufräumen**
- Modify: `src/ui/histogram.py` — `show_stats`-Parameter (Parität zum Desktop); `app.py` reicht ihn durch.
- Create: `src/analysis/rms.py` — `rss_series`-Helper (eine Quelle der RSS-Summe); Nutzung in `src/ui/spectrum.py`, `src/desktop/plots/spectrum_canvas.py`.
- Create: `src/desktop/app_runner.py` — gemeinsamer Bootstrap für beide Entrypoints.
- Modify: `desktop_main.py`, `packaging/entry.py`, `packaging/build.py` — Bootstrap/Logging konsolidieren.
- Modify: `src/core/settings.py` — `folders` als `tuple`; Docstring-Korrekturen in `src/ui/heatmap.py`, `src/ui/spectrum.py`, `src/analysis/grid.py`.

**Phase 4 — Optimieren** *(nach Review gestrichen — Export-Cache war wirkungslos + Leak; siehe Phase-4-Abschnitt)*

**Phase 5 — GUI/UX**
- Modify: `src/ui/strings.py`, `src/desktop/main_window.py`, `app.py` — Warte-Feedback um `analyze()` (Desktop-Cursor mit `processEvents`, Streamlit-Spinner).

---

## Phase 1 — Stabilisieren

### Task 1: numpy-`trapezoid`-Kompatibilitäts-Shim

**Files:**
- Modify: `src/analysis/rms.py:84`
- Test: `tests/analysis/test_rms.py`

**Hintergrund:** Der Rechenkern ruft `np.trapezoid` auf — diese Funktion existiert erst ab numpy 2.0. Der Shim macht den Code auf numpy 1.26 *und* 2.x lauffähig (defensive Absicherung; der harte Floor folgt in Task 2).

- [ ] **Step 1: Failing test schreiben**

In `tests/analysis/test_rms.py` am Dateiende ergänzen:

```python
def test_trapezoid_shim_resolves_and_integrates():
    # Der Shim muss unabhängig von der numpy-Version eine integrierbare Callable sein.
    from src.analysis.rms import _trapezoid

    y = np.array([1.0, 1.0, 1.0])
    x = np.array([0.0, 1.0, 2.0])
    # Integral einer konstanten 1 über [0, 2] = 2.0
    assert _trapezoid(y, x) == 2.0
```

(`import numpy as np` steht bereits oben in der Datei.)

- [ ] **Step 2: Test laufen lassen, Fehlschlag prüfen**

Run: `python -m pytest tests/analysis/test_rms.py::test_trapezoid_shim_resolves_and_integrates -v`
Expected: FAIL mit `ImportError: cannot import name '_trapezoid'`.

- [ ] **Step 3: Shim implementieren**

In `src/analysis/rms.py` direkt nach den Imports (nach `Axis = Literal["X", "Y", "Z", "RSS"]`) einfügen:

```python
# ``np.trapezoid`` existiert erst ab numpy 2.0; in 1.26 heißt die Funktion
# ``np.trapz``. Einmal auflösen, damit der Rechenkern auf beiden Versionen läuft.
_trapezoid = getattr(np, "trapezoid", None) or np.trapz
```

In `compute_band_rms` den Aufruf ersetzen — aus:

```python
    return float(
        np.sqrt(np.trapezoid(sub["integrand"].to_numpy(), sub["Frequenz_Hz"].to_numpy()))
    )
```

wird:

```python
    return float(
        np.sqrt(_trapezoid(sub["integrand"].to_numpy(), sub["Frequenz_Hz"].to_numpy()))
    )
```

- [ ] **Step 4: Tests laufen lassen, Erfolg prüfen**

Run: `python -m pytest tests/analysis/test_rms.py -v`
Expected: PASS (neuer Test + alle bestehenden RMS-Tests grün).

- [ ] **Step 5: Commit**

```bash
git add src/analysis/rms.py tests/analysis/test_rms.py
git commit -m "fix(rms): add numpy trapezoid compatibility shim for numpy <2.0"
```

---

### Task 2: numpy-Floor korrigieren und Runtime-Deps deklarieren

**Files:**
- Modify: `requirements.txt:7`
- Modify: `pyproject.toml:5-8`

**Hintergrund:** `requirements.txt` erlaubt `numpy>=1.26.0`, der Code braucht aber faktisch 2.0+. Außerdem stehen die Laufzeit-Deps nur in `requirements.txt`, nicht im Manifest.

- [ ] **Step 1: numpy-Floor anheben**

In `requirements.txt` die Zeile

```
numpy>=1.26.0
```

ersetzen durch:

```
numpy>=2.0.0
```

- [ ] **Step 2: Runtime-Deps im Manifest deklarieren**

In `pyproject.toml` den `[project]`-Block erweitern (nach `requires-python = ">=3.10"`):

```toml
[project]
name = "acc-visualisation"
version = "0.2.0"
requires-python = ">=3.10"
dependencies = [
    "PySide6>=6.6.0",
    "matplotlib>=3.8.0",
    "pandas>=2.1.0",
    "numpy>=2.0.0",
    "scipy>=1.12.0",
]

[project.optional-dependencies]
web = ["streamlit>=1.35.0", "plotly>=5.18.0"]
packaging = ["pyinstaller>=6.0"]
dev = ["pytest>=8.0.0"]
```

- [ ] **Step 3: Konsistenz verifizieren**

Run: `python -c "import numpy; assert hasattr(numpy, 'trapezoid'), numpy.__version__; print('ok', numpy.__version__)"`
Expected: `ok 2.x.y`

Run: `python -m pytest -q`
Expected: PASS (Baseline unverändert grün).

- [ ] **Step 4: Commit**

```bash
git add requirements.txt pyproject.toml
git commit -m "build: require numpy>=2.0 and declare runtime deps in pyproject"
```

---

### Task 3: Streamlit-Histogramm nutzt `hist_range` statt `z_range`

**Files:**
- Modify: `app.py:45-49` und `app.py:89-95`
- Test: `tests/ui/test_smoke.py`

**Hintergrund:** `analyze()` liefert bewusst zwei Bereiche: `z_range` (interpolierte Fläche → Heatmap-Farbskala) und `hist_range` (nur gemessene Werte → Histogramm-x-Achse). `app.py` ignoriert `hist_range` und füttert das Histogramm fälschlich mit `z_range`. Der Desktop macht es bereits korrekt (`main_window.py:247`). Die *Bereichs*-Korrektheit ist am Kern bereits durch `tests/core/test_pipeline.py::test_analyze_hist_range_ignores_interpolated_overshoot` abgesichert; dieser Task korrigiert die Verdrahtung und ergänzt einen Regressions-Smoke, der genau den Interpolations-/Shared-Scale-Pfad durchläuft.

- [ ] **Step 1: Echten Regressions-Test schreiben (fängt die Verdrahtung ab)**

Der Test fängt das tatsächlich an `make_histogram` übergebene `x_range` ab und vergleicht es mit dem *gemessenen* `hist_range`. So schlägt er fehl, solange `app.py` `z_range` füttert (kein Tautologie-/Smoke-Test). `streamlit.testing.v1.AppTest` führt das `app.py`-Skript bei jedem `run()` neu aus, daher wird `monkeypatch` auf das `histogram`-Modul von der `from … import make_histogram`-Zeile in `app.py` gesehen.

In `tests/ui/test_smoke.py` am Dateiende ergänzen:

```python
def test_app_histogram_uses_measured_hist_range_not_interpolated(tmp_path, monkeypatch):
    # Regression guard: das Streamlit-Histogramm muss mit dem gemessenen hist_range
    # gespeist werden, nie mit dem interpolierten z_range (das durch die große
    # Referenz in der Plattenmitte über das Messmaximum hinausschießt).
    from streamlit.testing.v1 import AppTest

    import src.ui.histogram as hist_mod
    from src.core.pipeline import analyze, load_plates
    from src.core.settings import Settings
    from tests.core.conftest import make_plate_folder

    folder = make_plate_folder(
        tmp_path / "p1",
        {(0, 0): 1e-3, (0, 2): 2e-3, (2, 0): 3e-3, (2, 2): 4e-3},
        ref_val=1.0,
    )

    # Erwartetes Ergebnis unabhängig von der App berechnen — mit den App-Defaults
    # (f_min=0, f_max=25000, axis=X, normalize off, interpolate+shared an).
    settings = Settings(
        folders=(("Platte 1", str(folder)),),
        f_min=0, f_max=25000, axis="X", normalize=False,
        shared_scale=True, colorscale="Viridis", interpolate=True,
    )
    res = analyze(load_plates(list(settings.folders)).plates, settings)
    expected_hist = res.hist_range
    assert expected_hist is not None
    assert res.z_range is not None and res.z_range[1] > expected_hist[1]  # Overshoot existiert

    captured: dict = {}
    real = hist_mod.make_histogram

    def capturing(values, **kwargs):
        captured["x_range"] = kwargs.get("x_range")
        return real(values, **kwargs)

    monkeypatch.setattr(hist_mod, "make_histogram", capturing)

    at = AppTest.from_file("app.py", default_timeout=60)
    at.session_state["accviz_folder1"] = str(folder)
    at.run()
    assert not at.exception
    assert captured["x_range"] == expected_hist
```

- [ ] **Step 2: Test laufen lassen, Fehlschlag prüfen**

Run: `python -m pytest "tests/ui/test_smoke.py::test_app_histogram_uses_measured_hist_range_not_interpolated" -v`
Expected: FAIL — `captured["x_range"]` ist aktuell `z_range` (mit Overshoot), nicht `expected_hist`.

- [ ] **Step 3: Verdrahtung in `app.py` korrigieren**

In `app.py` den Result-Block (Zeilen 45-49) um `hist_range` erweitern:

```python
result = analyze(plates, settings)
grids = result.grids
interp_grids = result.interp_grids
ref_rms = result.ref_rms
z_range = result.z_range
hist_range = result.hist_range
```

Im Histogramm-Aufruf (Zeilen 89-95) `x_range` von `z_range` auf `hist_range` umstellen:

```python
        hist_fig = make_histogram(
            grids[name].ravel(),
            bins=settings.histogram_bins,
            normalized=settings.normalize,
            ref_value=marker,
            x_range=hist_range if settings.shared_scale else None,
        )
```

- [ ] **Step 4: Tests laufen lassen, Erfolg prüfen**

Run: `python -m pytest tests/ui/test_smoke.py -v`
Expected: PASS (alle Smoke-Tests, inkl. neuem).

- [ ] **Step 5: Manuelle Sicht-Verifikation (Checkpoint, nicht automatisiert)**

Run: `python3 -m streamlit run app.py`
Aktion: Eine Platte mit Referenz laden, Interpolation + „Gemeinsame Farbskala“ aktiv. Prüfen: Die x-Achse des Histogramms endet beim größten *gemessenen* Wert, nicht beim (höheren) Referenz-/Interpolationswert.

- [ ] **Step 6: Commit**

```bash
git add app.py tests/ui/test_smoke.py
git commit -m "fix(streamlit): feed histogram measured hist_range instead of interpolated z_range"
```

---

### Task 4: Empty-State im Plotly-Heatmap (Streamlit) bei leerem Gitter

**Files:**
- Modify: `src/ui/heatmap.py`
- Test: `tests/ui/test_heatmap.py` (neu)

**Hintergrund:** Wenn das Frequenzband alle Werte ausschließt (z. B. `f_min == f_max`, kein Messpunkt im Band), ist das Gitter komplett NaN und die Heatmap rendert wortlos leer. Eine Annotation erklärt das.

- [ ] **Step 1: String ergänzen**

In `src/ui/strings.py` nach `HISTOGRAM_EMPTY = "Keine Daten für Histogramm."` einfügen:

```python
HEATMAP_EMPTY = "Keine Messwerte im gewählten Frequenzband."
```

- [ ] **Step 2: Failing tests schreiben**

Neue Datei `tests/ui/test_heatmap.py`:

```python
from __future__ import annotations

import numpy as np
import plotly.graph_objects as go

from src.ui.heatmap import make_heatmap


def _make(grid):
    return make_heatmap(
        grid,
        title="P1",
        colorscale="Viridis",
        normalized=False,
        hole_positions=[],
        hole_values=[],
        ref_value=None,
        z_range=None,
    )


def test_make_heatmap_all_nan_shows_empty_annotation():
    grid = np.full((3, 3), np.nan)
    fig = _make(grid)
    texts = [a.text for a in fig.layout.annotations]
    assert any("Frequenzband" in t for t in texts)


def test_make_heatmap_with_data_has_heatmap_trace_and_no_empty_annotation():
    grid = np.array([[1.0, 2.0], [3.0, 4.0]])
    fig = _make(grid)
    assert any(isinstance(t, go.Heatmap) for t in fig.data)
    texts = [a.text for a in fig.layout.annotations]
    assert not any("Frequenzband" in t for t in texts)
```

- [ ] **Step 3: Tests laufen lassen, Fehlschlag prüfen**

Run: `python -m pytest tests/ui/test_heatmap.py -v`
Expected: `test_make_heatmap_all_nan_shows_empty_annotation` FAIL (keine passende Annotation).

- [ ] **Step 4: Empty-State implementieren**

In `src/ui/heatmap.py` am Anfang von `make_heatmap` (direkt nach `nrows, ncols = grid.shape` / vor dem `fig = go.Figure(...)`-Block) einsetzen:

```python
    nrows, ncols = grid.shape
    label = S.COLORBAR_NORMALIZED if normalized else S.COLORBAR_ABSOLUTE

    if not np.isfinite(grid).any():
        fig = go.Figure()
        fig.add_annotation(
            text=S.HEATMAP_EMPTY,
            xref="paper", yref="paper", x=0.5, y=0.5, showarrow=False,
        )
        fig.update_layout(
            title=title,
            height=HEATMAP_HEIGHT,
            xaxis=dict(visible=False),
            yaxis=dict(visible=False),
        )
        return fig
```

(Die bestehende `label`-Zuweisung weiter unten kann bleiben oder entfallen — sie ist idempotent; beim Aufräumen optional die Dopplung entfernen.)

- [ ] **Step 5: Tests laufen lassen, Erfolg prüfen**

Run: `python -m pytest tests/ui/test_heatmap.py -v`
Expected: PASS (beide Tests).

- [ ] **Step 6: Commit**

```bash
git add src/ui/heatmap.py src/ui/strings.py tests/ui/test_heatmap.py
git commit -m "feat(streamlit): show empty-state annotation when heatmap grid is all-NaN"
```

---

### Task 5: Empty-State im matplotlib-Heatmap (Desktop) bei leerem Gitter

**Files:**
- Modify: `src/desktop/plots/heatmap_canvas.py`
- Test: `tests/desktop/test_heatmap_canvas.py`

- [ ] **Step 1: Failing test schreiben**

In `tests/desktop/test_heatmap_canvas.py` am Dateiende ergänzen:

```python
def test_render_grid_all_nan_shows_empty_text(qapp):
    canvas = HeatmapCanvas()
    grid = np.full((3, 3), np.nan)
    canvas.render_grid(
        grid,
        plate_name="P1",
        title="P1",
        colorscale="Viridis",
        normalized=False,
        hole_positions=[],
        hole_values=[],
        ref_value=None,
        z_range=None,
    )
    texts = [t.get_text() for t in canvas.axes.texts]
    assert any("Frequenzband" in t for t in texts)
```

(`HeatmapCanvas` und `np` sind in der Datei bereits importiert; `qapp` kommt aus der desktop-conftest.)

- [ ] **Step 2: Test laufen lassen, Fehlschlag prüfen**

Run: `QT_QPA_PLATFORM=offscreen python -m pytest tests/desktop/test_heatmap_canvas.py::test_render_grid_all_nan_shows_empty_text -v`
Expected: FAIL (kein passender Text auf den Axes).

- [ ] **Step 3: Empty-State implementieren**

In `src/desktop/plots/heatmap_canvas.py`, in `render_grid`, direkt nach `nrows, ncols = grid.shape` (vor `self._figure.clear()`-Folgeblock) den leeren Fall abfangen:

```python
        nrows, ncols = grid.shape

        if not np.isfinite(grid).any():
            self._figure.clear()
            self.axes = self._figure.add_subplot(111)
            self._colorbar = None  # alte Colorbar-Referenz nicht hängen lassen
            self.axes.text(
                0.5, 0.5, S.HEATMAP_EMPTY,
                ha="center", va="center", transform=self.axes.transAxes,
            )
            self.axes.set_xticks([])
            self.axes.set_yticks([])
            self.axes.set_title(title)
            self.draw_idle()
            return
```

(`S.HEATMAP_EMPTY` wurde in Task 4 angelegt.)

- [ ] **Step 4: Tests laufen lassen, Erfolg prüfen**

Run: `QT_QPA_PLATFORM=offscreen python -m pytest tests/desktop/test_heatmap_canvas.py -v`
Expected: PASS (neuer Test + bestehende).

- [ ] **Step 5: Commit**

```bash
git add src/desktop/plots/heatmap_canvas.py tests/desktop/test_heatmap_canvas.py
git commit -m "feat(desktop): show empty-state text when heatmap grid is all-NaN"
```

---

### Task 6: Desktop-Frequenzband erzwingt `f_max > f_min`

**Files:**
- Modify: `src/desktop/control_panel.py:213-227`
- Test: `tests/desktop/test_control_panel.py`

**Hintergrund:** Die SpinBox-Clamps erlauben `f_min == f_max`, was den gesamten Rechenpfad NaN liefern lässt. Ein Mindestabstand von einem Schritt (100 Hz) verhindert das. Am oberen Anschlag (25000) muss `f_min` nach unten gezogen werden statt `f_max` über den Bereich.

- [ ] **Step 1: Failing tests schreiben**

In `tests/desktop/test_control_panel.py` am Dateiende ergänzen:

```python
def test_f_min_pushes_f_max_to_keep_strict_order(qapp):
    panel = ControlPanel()
    panel.set_frequency_band(0, 1000)
    panel._f_min.setValue(1000)  # gleich f_max -> muss f_max hochschieben
    s = panel.current_settings()
    assert s.f_max > s.f_min


def test_f_min_at_ceiling_pulls_itself_below_max(qapp):
    panel = ControlPanel()
    panel._f_max.setValue(25000)
    panel._f_min.setValue(25000)  # am Anschlag -> f_min muss unter f_max rutschen
    s = panel.current_settings()
    assert s.f_min < s.f_max
    assert s.f_max == 25000
```

- [ ] **Step 2: Tests laufen lassen, Fehlschlag prüfen**

Run: `QT_QPA_PLATFORM=offscreen python -m pytest tests/desktop/test_control_panel.py::test_f_min_pushes_f_max_to_keep_strict_order tests/desktop/test_control_panel.py::test_f_min_at_ceiling_pulls_itself_below_max -v`
Expected: FAIL (aktuell ist `f_min == f_max` erlaubt).

- [ ] **Step 3: Strikten Abstand implementieren**

In `src/desktop/control_panel.py` eine Konstante neben den Property-Keys ergänzen (nach `_METHOD_PROP = "method_value"`):

```python
_FREQ_STEP = 100  # Hz; Mindestabstand zwischen f_min und f_max
```

`_on_f_min_changed` und `_on_f_max_changed` ersetzen:

```python
    def _on_f_min_changed(self, value: int) -> None:
        # f_max muss strikt größer bleiben. Signale während des Clamps blocken,
        # damit pro Nutzer-Edit genau ein settingsChanged ausgelöst wird.
        if value >= self._f_max.value():
            target = value + _FREQ_STEP
            if target <= self._f_max.maximum():
                self._f_max.blockSignals(True)
                self._f_max.setValue(target)
                self._f_max.blockSignals(False)
            else:
                # f_max am Anschlag: f_min unter f_max ziehen.
                self._f_min.blockSignals(True)
                self._f_min.setValue(self._f_max.value() - _FREQ_STEP)
                self._f_min.blockSignals(False)
        self.settingsChanged.emit()

    def _on_f_max_changed(self, value: int) -> None:
        if value <= self._f_min.value():
            target = value - _FREQ_STEP
            if target >= self._f_min.minimum():
                self._f_min.blockSignals(True)
                self._f_min.setValue(target)
                self._f_min.blockSignals(False)
            else:
                self._f_max.blockSignals(True)
                self._f_max.setValue(self._f_min.value() + _FREQ_STEP)
                self._f_max.blockSignals(False)
        self.settingsChanged.emit()
```

- [ ] **Step 4: Tests laufen lassen, Erfolg prüfen**

Run: `QT_QPA_PLATFORM=offscreen python -m pytest tests/desktop/test_control_panel.py -v`
Expected: PASS (neue + bestehende, inkl. `test_current_settings_reflects_widget_changes`).

- [ ] **Step 5: Commit**

```bash
git add src/desktop/control_panel.py tests/desktop/test_control_panel.py
git commit -m "fix(desktop): enforce f_max > f_min in frequency band controls"
```

---

## Phase 2 — Absichern

### Task 7: CI um pyright und breitere Python-Matrix erweitern

**Files:**
- Modify: `.github/workflows/ci.yml:18-33`

**Hintergrund:** `requires-python = ">=3.10"`, getestet wird nur 3.11; der 3.10-Logging-Fallback (`src/logging_setup.py:11`) ist ungetestet. `pyrightconfig.json` existiert, läuft aber nicht in CI.

- [ ] **Step 1: Python-Matrix erweitern**

In `.github/workflows/ci.yml` im `test`-Job die Matrix ergänzen:

```yaml
  test:
    strategy:
      fail-fast: false
      matrix:
        os: [ubuntu-latest, macos-latest, windows-latest]
        python-version: ["3.10", "3.11", "3.12"]
    runs-on: ${{ matrix.os }}
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: ${{ matrix.python-version }}
```

- [ ] **Step 2: pyright-Step ergänzen (non-blocking, gepinnt)**

Der Code hat aktuell 13 pyright-Errors (überwiegend in den Tests, z. B. `tests/core/test_pipeline.py:17`/`:114`). Ein blockierender Step würde CI sofort rot färben. Daher non-blocking (`continue-on-error: true`) und die Version pinnen, damit nicht ein pyright-Update CI nichtdeterministisch bricht. Sobald die 13 Errors separat bereinigt sind, kann `continue-on-error` entfallen (Folge-Task).

Im `test`-Job nach „Install deps“ und vor „Run tests“ einfügen:

```yaml
      - name: Type-check (pyright, informational)
        continue-on-error: true
        run: |
          pip install pyright==1.1.410
          pyright
```

- [ ] **Step 3: Workflow-Syntax lokal prüfen**

Run: `python -c "import yaml; yaml.safe_load(open('.github/workflows/ci.yml')); print('yaml ok')"`
Expected: `yaml ok`

- [ ] **Step 4: pyright lokal gegenchecken (informativ)**

Run: `pyright 2>&1 | tail -3`
Expected: Weiterhin ~13 vorbestehende Errors (in den Tests), aber **keine neuen** durch die Phase-1/3-Änderungen. Der CI-Step ist non-blocking, bricht den Lauf also nicht ab.

- [ ] **Step 5: Commit**

```bash
git add .github/workflows/ci.yml
git commit -m "ci: add pyright type-check and test on Python 3.10/3.11/3.12"
```

---

## Phase 3 — Aufräumen

### Task 8: Statistik-Overlay-Parität — `show_stats` für das Streamlit-Histogramm

**Files:**
- Modify: `src/ui/histogram.py`
- Modify: `app.py:89-95`
- Test: `tests/ui/test_histogram.py`

**Hintergrund:** Das Statistik-Overlay (µ/Median/±1σ) existiert nur im Desktop (`histogram_canvas.render_values(show_stats=...)`); `Settings.histogram_stats` (Default `True`) bleibt in Streamlit wirkungslos. Strings (`HISTOGRAM_STAT_MEAN/MEDIAN/SIGMA`) existieren bereits.

**⚠ Abhängigkeit:** Step 4 editiert denselben `make_histogram`-Aufruf in `app.py` wie Task 3 und nutzt das dort eingeführte lokale `hist_range`. Task 8 **muss nach Task 3** laufen, sonst `NameError: hist_range`. Bei subagent-getriebener Ausführung strikt sequenziell halten.

- [ ] **Step 1: Failing tests schreiben**

In `tests/ui/test_histogram.py` am Dateiende ergänzen:

```python
def test_make_histogram_show_stats_adds_stat_lines():
    values = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
    fig = make_histogram(values, bins=5, normalized=False, show_stats=True)
    # mean, median, -1σ, +1σ => mindestens 4 vertikale Linien (Shapes)
    assert len(fig.layout.shapes) >= 4


def test_make_histogram_show_stats_default_off():
    values = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
    fig = make_histogram(values, bins=5, normalized=False)
    assert len(fig.layout.shapes) == 0
```

- [ ] **Step 2: Tests laufen lassen, Fehlschlag prüfen**

Run: `python -m pytest tests/ui/test_histogram.py::test_make_histogram_show_stats_adds_stat_lines -v`
Expected: FAIL mit `TypeError: ... unexpected keyword argument 'show_stats'`.

- [ ] **Step 3: `show_stats` in `make_histogram` implementieren**

In `src/ui/histogram.py` die Signatur erweitern (nach `x_range`):

```python
def make_histogram(
    values: np.ndarray,
    *,
    bins: int,
    normalized: bool,
    ref_value: float | None = None,
    x_range: tuple[float, float] | None = None,
    show_stats: bool = False,
) -> go.Figure:
```

Nach dem `ref_value`-Block (nach `fig.add_vline(... ref_value ...)`) ergänzen:

```python
    if show_stats and finite.size >= 2:
        mean = float(np.mean(finite))
        median = float(np.median(finite))
        std = float(np.std(finite))
        fig.add_vline(
            x=mean, line=dict(color="#D62728", width=2),
            annotation_text=S.HISTOGRAM_STAT_MEAN.format(value=mean),
        )
        fig.add_vline(
            x=median, line=dict(color="#2CA02C", dash="dash", width=2),
            annotation_text=S.HISTOGRAM_STAT_MEDIAN.format(value=median),
        )
        fig.add_vline(x=mean - std, line=dict(color="#9467BD", dash="dot", width=1.5))
        fig.add_vline(
            x=mean + std, line=dict(color="#9467BD", dash="dot", width=1.5),
            annotation_text=S.HISTOGRAM_STAT_SIGMA.format(value=std),
        )
```

- [ ] **Step 4: In `app.py` durchreichen**

Im Histogramm-Aufruf in `app.py` `show_stats` ergänzen:

```python
        hist_fig = make_histogram(
            grids[name].ravel(),
            bins=settings.histogram_bins,
            normalized=settings.normalize,
            ref_value=marker,
            x_range=hist_range if settings.shared_scale else None,
            show_stats=settings.histogram_stats,
        )
```

- [ ] **Step 5: Tests laufen lassen, Erfolg prüfen**

Run: `python -m pytest tests/ui/test_histogram.py tests/ui/test_smoke.py -v`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add src/ui/histogram.py app.py tests/ui/test_histogram.py
git commit -m "feat(streamlit): add histogram stats overlay for frontend parity with desktop"
```

---

### Task 9: RSS-Summe in einen einzigen Helper konsolidieren

**Files:**
- Modify: `src/analysis/rms.py`
- Modify: `src/ui/spectrum.py:90-92` und `:103-105`
- Modify: `src/desktop/plots/spectrum_canvas.py:28-30`
- Test: `tests/analysis/test_rms.py`

**Hintergrund:** `PSD_X_g2Hz + PSD_Y_g2Hz + PSD_Z_g2Hz` ist an ~5 Stellen eigenständig implementiert. Eine zentrale Funktion verhindert Drift.

- [ ] **Step 1: Failing test schreiben**

In `tests/analysis/test_rms.py` am Dateiende ergänzen:

```python
def test_rss_series_sums_three_axes():
    import pandas as pd

    from src.analysis.rms import rss_series

    df = pd.DataFrame({
        "Frequenz_Hz": [0.0, 1.0],
        "PSD_X_g2Hz": [1.0, 2.0],
        "PSD_Y_g2Hz": [3.0, 4.0],
        "PSD_Z_g2Hz": [5.0, 6.0],
    })
    result = rss_series(df)
    assert list(result) == [9.0, 12.0]
```

- [ ] **Step 2: Test laufen lassen, Fehlschlag prüfen**

Run: `python -m pytest tests/analysis/test_rms.py::test_rss_series_sums_three_axes -v`
Expected: FAIL mit `ImportError: cannot import name 'rss_series'`.

- [ ] **Step 3: Helper implementieren und Aufrufer umstellen**

In `src/analysis/rms.py` nach `_trapezoid` ergänzen:

```python
def rss_series(df: pd.DataFrame) -> pd.Series:
    """Per-frequency sum ``PSD_X + PSD_Y + PSD_Z`` (vor Clipping/Integration)."""
    return df["PSD_X_g2Hz"] + df["PSD_Y_g2Hz"] + df["PSD_Z_g2Hz"]
```

In `_integrand_series` (`src/analysis/rms.py`) den RSS-Zweig umstellen:

```python
    if axis == "RSS":
        return rss_series(df)
    return df[f"PSD_{axis}_g2Hz"]
```

In `src/ui/spectrum.py` oben importieren:

```python
from src.analysis.rms import rss_series
```

und die beiden Summen in `_add_rss_traces` ersetzen — aus
`sum_series = (hole_df["PSD_X_g2Hz"] + hole_df["PSD_Y_g2Hz"] + hole_df["PSD_Z_g2Hz"]).clip(lower=1e-30)`
wird `sum_series = rss_series(hole_df).clip(lower=1e-30)`, und analog
`ref_sum = rss_series(ref_df).clip(lower=1e-30)`.

In `src/desktop/plots/spectrum_canvas.py` `_rss_sum` umstellen:

```python
from src.analysis.rms import rss_series

def _rss_sum(df: pd.DataFrame) -> pd.Series:
    """Per-frequency sum of the three axis PSDs, floored for the log y-axis."""
    return rss_series(df).clip(lower=_FLOOR)
```

- [ ] **Step 4: Tests laufen lassen, Erfolg prüfen**

Run: `QT_QPA_PLATFORM=offscreen python -m pytest tests/analysis tests/ui/test_strings.py tests/desktop/test_plot_canvases.py -v`
Expected: PASS. Danach Vollauf: `python -m pytest -q` → PASS.

- [ ] **Step 5: Commit**

```bash
git add src/analysis/rms.py src/ui/spectrum.py src/desktop/plots/spectrum_canvas.py tests/analysis/test_rms.py
git commit -m "refactor: consolidate PSD RSS sum into single rss_series helper"
```

---

### Task 10: Gemeinsamer App-Bootstrap für beide Entrypoints

**Files:**
- Create: `src/desktop/app_runner.py`
- Modify: `desktop_main.py`
- Modify: `packaging/entry.py`
- Modify: `packaging/build.py:66-69`
- Test: `tests/desktop/test_app_runner.py` (neu)

**Hintergrund:** `desktop_main.py` und `packaging/entry.py` duplizieren den QApplication-Start; beide (und `build.py`) konfigurieren Logging von Hand statt `logging_setup.configure_logging` zu nutzen.

- [ ] **Step 1: Failing test schreiben**

Neue Datei `tests/desktop/test_app_runner.py`:

```python
from __future__ import annotations


def test_build_main_window_returns_window(qapp):
    from src.desktop.app_runner import build_main_window

    window = build_main_window()
    assert window is not None
    assert window.windowTitle()  # nicht-leerer Titel
```

- [ ] **Step 2: Test laufen lassen, Fehlschlag prüfen**

Run: `QT_QPA_PLATFORM=offscreen python -m pytest tests/desktop/test_app_runner.py -v`
Expected: FAIL mit `ModuleNotFoundError: No module named 'src.desktop.app_runner'`.

- [ ] **Step 3: `app_runner` implementieren**

Neue Datei `src/desktop/app_runner.py`:

```python
from __future__ import annotations

"""Shared bootstrap for the native desktop app, used by both entrypoints.

Centralizes QApplication setup so ``desktop_main.py`` (dev) and
``packaging/entry.py`` (frozen) stay in sync.
"""

import os

from src.logging_setup import get_logger

_LOG = get_logger(__name__)


def build_main_window():
    """Instantiate and return the application's main window (without showing)."""
    from src.desktop.main_window import MainWindow

    return MainWindow()


def run_app(argv: list[str], *, smoke: bool = False) -> int:
    """Create the QApplication, show the main window, run the event loop.

    Args:
        argv: Process argv handed to QApplication.
        smoke: When True, auto-quit shortly after start (for headless smoke tests).
    """
    from PySide6.QtWidgets import QApplication

    app = QApplication.instance() or QApplication(argv)
    window = build_main_window()
    window.show()
    _LOG.info("Desktop app started")

    if smoke or os.environ.get("ACC_VIZ_SMOKE") == "1":
        from PySide6.QtCore import QTimer

        QTimer.singleShot(1500, app.quit)

    return app.exec()
```

- [ ] **Step 4: `desktop_main.py` auf den Runner umstellen**

`desktop_main.py` ersetzen durch:

```python
from __future__ import annotations

"""Entry point for the native PySide6 desktop application.

Run with ``python desktop_main.py``. This replaces the Streamlit web app
(``app.py``) for the packaged, native desktop build.
"""

import sys

from src.desktop.app_runner import run_app


def main() -> int:
    return run_app(sys.argv)


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 5: `packaging/entry.py` auf den Runner umstellen**

In `packaging/entry.py` den Body von `main()` ersetzen (Frozen-Pfad-Handling bleibt, Bootstrap geht an den Runner):

```python
def main() -> int:
    # When frozen, PyInstaller unpacks to sys._MEIPASS; otherwise use repo root.
    base = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent.parent))
    os.chdir(base)
    if str(base) not in sys.path:
        sys.path.insert(0, str(base))

    from src.desktop.app_runner import run_app

    return run_app(sys.argv)
```

Die manuelle `logging.basicConfig(...)`-Zeile und der nun ungenutzte `import logging` in `entry.py` entfallen (Logging übernimmt `logging_setup` via Runner).

- [ ] **Step 6: `packaging/build.py` Logging vereinheitlichen**

In `packaging/build.py` den `if __name__ == "__main__"`-Block ersetzen:

```python
if __name__ == "__main__":
    from src.logging_setup import configure_logging

    configure_logging()
    main()
```

(Den `import logging` in `build.py` belassen — `_LOG = logging.getLogger(__name__)` nutzt ihn weiterhin.)

- [ ] **Step 7: Tests laufen lassen, Erfolg prüfen**

Run: `QT_QPA_PLATFORM=offscreen python -m pytest tests/desktop -v`
Expected: PASS (neuer Runner-Test + alle Desktop-Tests).

- [ ] **Step 8: Commit**

```bash
git add src/desktop/app_runner.py desktop_main.py packaging/entry.py packaging/build.py tests/desktop/test_app_runner.py
git commit -m "refactor(desktop): share app bootstrap and unify logging across entrypoints"
```

---

### Task 11: `Settings.folders` immutabel + Docstring-Korrekturen

**Files:**
- Modify: `src/core/settings.py:49`
- Modify: `src/ui/sidebar.py:103-120`, `src/desktop/control_panel.py:255-282`
- Modify: `src/ui/heatmap.py:37`, `src/ui/spectrum.py:34-35,144-145`, `src/analysis/grid.py:42-44`
- Test: `tests/core/test_settings.py`

**Hintergrund:** `frozen=True` schützt die Listenreferenz, nicht den Inhalt; die Desktop-Caching-Logik vergleicht `Settings`-Instanzen. Ein `tuple` macht den Wert echt unveränderlich (gleiches `__eq__`). Mehrere Docstrings behaupten „1-indexed“, obwohl Koordinaten 0-indexiert sind.

- [ ] **Step 1: Failing test schreiben**

In `tests/core/test_settings.py` am Dateiende ergänzen:

```python
def test_settings_folders_is_tuple_and_hashable_value():
    from src.core.settings import Settings

    s = Settings(
        folders=(("Platte 1", "/a"),),
        f_min=0, f_max=10, axis="X", normalize=False,
        shared_scale=True, colorscale="Viridis",
    )
    assert isinstance(s.folders, tuple)
    # Gleichheit bleibt strukturell (Caching-Vergleich im Desktop hängt daran).
    s2 = Settings(
        folders=(("Platte 1", "/a"),),
        f_min=0, f_max=10, axis="X", normalize=False,
        shared_scale=True, colorscale="Viridis",
    )
    assert s == s2
```

- [ ] **Step 2: Test laufen lassen, Fehlschlag prüfen**

Run: `python -m pytest tests/core/test_settings.py::test_settings_folders_is_tuple_and_hashable_value -v`
Expected: FAIL (`folders` ist aktuell `list`).

- [ ] **Step 3: Typ auf `tuple` umstellen**

In `src/core/settings.py` das Feld ändern:

```python
    folders: tuple[tuple[str, str], ...]  # (label, raw path)
```

In `src/ui/sidebar.py` die Folder-Sammlung (Zeilen 103-107) und den Return auf ein Tuple bringen:

```python
    folders: list[tuple[str, str]] = []
    if p1:
        folders.append(("Platte 1", p1))
    if p2:
        folders.append(("Platte 2", p2))

    return Settings(
        folders=tuple(folders),
        ...
    )
```

In `src/desktop/control_panel.py` in `current_settings` ebenfalls `folders=tuple(folders)` an `Settings(...)` übergeben (die lokale Sammlung darf `list` bleiben, nur die Übergabe wird zum Tuple).

- [ ] **Step 3b: Bestehende Tests an den Tuple-Typ anpassen (PFLICHT — sonst bricht Step 5)**

`current_settings()` liefert nun `folders == ()`, und in Python ist **`() == []` → `False`**. Daher den vorhandenen Test reparieren — in `tests/desktop/test_control_panel.py:37`:

```python
    assert s.folders == ()  # vorher: == []
```

Quer-Check der übrigen `folders`-Assertions: `tests/ui/test_sidebar.py` vergleicht via `len(...)` → bleibt gültig. `tests/core/test_pipeline.py` (`_settings`-Helper) und `tests/core/test_settings.py` konstruieren `Settings(folders=[...])` mit List-Literalen; das funktioniert weiter (die Dataclass coerct den Typ nicht), aber keine dieser Stellen vergleicht `folders` direkt gegen ein Literal — falls doch eine auftaucht, auf `(...)` umstellen.

Run: `python -m pytest tests/desktop/test_control_panel.py tests/ui/test_sidebar.py -v`
Expected: PASS (insb. der reparierte `:37`-Test).

- [ ] **Step 4: Docstrings korrigieren**

- `src/ui/heatmap.py:37`: „1-indexed“ → „0-indexed“; in `:32` Form `(max_x, max_y)` → `(max_x + 1, max_y + 1)`.
- `src/ui/spectrum.py:34-35` und `:144-145`: „1-indexed x/y coordinate“ → „0-indexed“.
- `src/analysis/grid.py`: sicherstellen, dass der Docstring die 0-Indexierung und Form `(max_x + 1, max_y + 1)` korrekt nennt (bereits größtenteils korrekt — nur prüfen/angleichen).

- [ ] **Step 5: Tests laufen lassen, Erfolg prüfen**

Run: `python -m pytest -q`
Expected: PASS (Vollauf; insbesondere `tests/core`, `tests/ui/test_sidebar.py`, `tests/desktop/test_control_panel.py`).

- [ ] **Step 6: Commit**

```bash
git add src/core/settings.py src/ui/sidebar.py src/desktop/control_panel.py src/ui/heatmap.py src/ui/spectrum.py src/analysis/grid.py tests/core/test_settings.py
git commit -m "refactor: make Settings.folders an immutable tuple; fix 0-index docstrings"
```

---

## Phase 4 — Optimieren *(nach Review gestrichen)*

> **Ursprünglich „Task 12: Export-CSV in Streamlit cachen“ — beim adversen Plan-Review (2026-06-16) verworfen.**
> Der vorgeschlagene `@st.cache_data(hash_funcs={dict: id})`-Wrapper keyt auf `id(plates)`; `app.py` baut das äußere `plates`-dict aber pro Rerun neu auf ([pipeline.py:128](src/core/pipeline.py:128)), sodass der Cache **bei jedem Rerun verfehlt** und zugleich **unbegrenzt wächst** (eine Entry pro Rerun). Ergebnis: kein Speedup, aber ein Memory-Leak. Der Test war nur grün, weil er dieselbe `plates`-Instanz zweimal verwendet. Ein *korrekter* Skalar-Key (Ordnerpfade + mtime + f_min/f_max/axis) wäre möglich, dupliziert aber die Load-Logik; angesichts des ursprünglich nur als NIEDRIG eingestuften Findings nicht gerechtfertigt. Bewusst nicht umgesetzt.

---

## Phase 5 — GUI/UX

### Task 12: Warte-Feedback um die Analyse

**Files:**
- Modify: `src/ui/strings.py`
- Modify: `src/desktop/main_window.py:136-142`
- Modify: `app.py:45`
- Test: `tests/desktop/test_main_window.py`

**Hintergrund:** Die scipy-Interpolation in `analyze()` läuft synchron im UI-Thread (Desktop) bzw. ohne Spinner (Streamlit). Ein Busy-Cursor/Spinner gibt sichtbares Feedback.

**Review-Hinweis:** `analyze()` läuft synchron in `_refresh`; ein bloßes `setOverrideCursor`+`restoreOverrideCursor` würde den Cursor setzen und zurücksetzen, **bevor** die Event-Loop ihn zeichnet — er wäre nie sichtbar. Deshalb in Step 3 ein `processEvents()` zwischen Cursor-Setzen und `analyze()`. Der Test in Step 1 ist bewusst ein Invarianten-Smoke („Cursor bleibt nie hängen“), kein Beweis der Sichtbarkeit; ein echtes Threading-Feedback ist ein bewusster Folge-Task.

- [ ] **Step 1: Failing test schreiben**

In `tests/desktop/test_main_window.py` am Dateiende ergänzen:

```python
def test_refresh_resets_override_cursor(qapp, tmp_path):
    from PySide6.QtWidgets import QApplication

    from src.desktop.main_window import MainWindow
    from tests.core.conftest import make_plate_folder

    folder = make_plate_folder(tmp_path / "p1", {(0, 0): 1e-3, (1, 1): 4e-3})
    win = MainWindow()
    win.control_panel.set_folder(0, str(folder))
    # Nach dem (synchronen) Refresh darf kein Override-Cursor hängen bleiben.
    assert QApplication.overrideCursor() is None
```

- [ ] **Step 2: Test laufen lassen, Status prüfen**

Run: `QT_QPA_PLATFORM=offscreen python -m pytest tests/desktop/test_main_window.py::test_refresh_resets_override_cursor -v`
Expected: PASS bereits jetzt (noch kein Override-Cursor) — der Test fixiert die Invariante „Cursor wird immer zurückgesetzt“ für die folgende Änderung.

- [ ] **Step 3a: Dedizierten String ergänzen**

In `src/ui/strings.py` nach `LOADING_PLATE = "Lade {label} …"` einfügen (vermeidet das doppelte „… …", das `LOADING_PLATE.format(label="Analyse …")` erzeugen würde):

```python
ANALYZING = "Analyse läuft …"
```

- [ ] **Step 3b: Busy-Cursor um `analyze()` legen (Desktop, mit `processEvents`)**

In `src/desktop/main_window.py`, im `_refresh`, den `analyze`-Block in Cursor-Handling kapseln:

```python
        compute_changed = prev is None or any(
            getattr(prev, f) != getattr(settings, f) for f in _COMPUTE_FIELDS
        )
        analysis = self._analysis
        if compute_changed or analysis is None:
            from PySide6.QtCore import Qt
            from PySide6.QtWidgets import QApplication

            QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
            # Cursor sofort zeichnen, bevor der synchrone analyze()-Aufruf blockiert.
            QApplication.processEvents()
            try:
                analysis = analyze(load.plates, settings)
            finally:
                QApplication.restoreOverrideCursor()
            self._analysis = analysis
```

- [ ] **Step 4: Spinner um `analyze()` (Streamlit)**

In `app.py` Zeile 45 ersetzen:

```python
with st.spinner(S.ANALYZING):
    result = analyze(plates, settings)
```

- [ ] **Step 5: Tests laufen lassen, Erfolg prüfen**

Run: `QT_QPA_PLATFORM=offscreen python -m pytest tests/desktop/test_main_window.py tests/ui/test_smoke.py -v`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add src/ui/strings.py src/desktop/main_window.py app.py tests/desktop/test_main_window.py
git commit -m "feat(ux): show busy feedback during analysis (desktop cursor, streamlit spinner)"
```

---

## Abschluss: Versions-Bump

### Task 13: Version auf 0.3.0 anheben, taggen, pushen

**Files:**
- Modify: `pyproject.toml:7`
- Modify: `README.md:1`

**Hintergrund:** MINOR-Bump (neue, abwärtskompatible Features: Histogramm-Stats in Streamlit, Empty-States, Warte-Feedback) gemäß SemVer-Workflow.

- [ ] **Step 1: Vollständige Verifikation**

Run: `python -m pytest -q`
Expected: PASS (alle Tests grün).

- [ ] **Step 2: Version in allen Quellen anheben**

In `pyproject.toml`: `version = "0.2.0"` → `version = "0.3.0"`.
In `README.md` (erste Zeile): Badge `version-0.2.0-blue` → `version-0.3.0-blue`.

- [ ] **Step 3: Konsistenz-Check**

Run: `grep -rn "0\.3\.0" pyproject.toml README.md && git tag | grep -c v0.3.0`
Expected: Beide Stellen zeigen `0.3.0`; `0` (Tag existiert noch nicht).

- [ ] **Step 4: Commit + annotierter Tag + Push**

```bash
git add pyproject.toml README.md
git commit -m "chore: bump version to 0.3.0"
git tag -a v0.3.0 -m "v0.3.0"
git push --follow-tags
```

(Der Versions-Workflow autorisiert diesen Push ohne Rückfrage.)

---

## Self-Review (vom Plan-Autor durchgeführt)

**Spec-Abdeckung (Audit-Findings → Task):**
- HOCH numpy-Floor → Task 1 + 2. ✓
- MITTEL Histogramm `z_range` vs `hist_range` → Task 3. ✓
- MITTEL `f_min == f_max` → Task 6 (Desktop-Guard) + Task 4/5 (Empty-State als Cross-Frontend-Auffang). ✓
- MITTEL Statistik-Overlay-Divergenz → Task 8 (läuft nach Task 3, siehe Abhängigkeit). ✓
- MITTEL kein Feedback während Analyse → Task 12 (mit `processEvents`, sonst No-op). ✓
- MITTEL keine app.py-Tests → Task 3 (echter Capture-Regressions-Test auf `x_range`). ✓
- NIEDRIG doppelter Bootstrap/Logging → Task 10. ✓
- NIEDRIG RSS-Summe dupliziert → Task 9. ✓
- NIEDRIG Docstrings 0/1-indexiert → Task 11. ✓
- NIEDRIG `Settings.folders` mutable → Task 11 (inkl. Reparatur von `test_control_panel.py:37`). ✓
- NIEDRIG Export bei jedem Rerun → **nach Review gestrichen** (Cache war wirkungslos + Leak; siehe Phase-4-Abschnitt). Bewusst offen.
- NIEDRIG Empty-State ohne Meldung → Task 4 + 5. ✓
- NIEDRIG CI: Deps/pyright/Python-Matrix → Task 2 + 7 (pyright non-blocking). ✓
- INFO „strict mode“ Laden → bewusst, kein Task (im Audit als by-design markiert). ✓
- NIEDRIG `main_window.py` nähert sich GUI-Entry-Grenze → **bewusst nicht eingeplant** (305 Zeilen, unter Schwelle; erst bei nächster Funktionserweiterung splitten). Dokumentiert, kein Task.

**Placeholder-Scan:** keine TBD/TODO/„handle edge cases“; jeder Code-Step zeigt vollständigen Code. ✓

**Typ-Konsistenz:** `_trapezoid`/`rss_series` (Task 1/9) konsistent benannt und genutzt; `show_stats` (Task 8) identisch zur Desktop-Signatur; `Settings.folders: tuple` (Task 11) konsistent in beiden Frontends + bestehende Tests angepasst; `ANALYZING`-String (Task 12) in `strings.py` definiert und in `app.py` genutzt; `build_main_window`/`run_app` (Task 10) gleich in Test, Runner und Entrypoints. ✓

**Adverser Review (2026-06-16, Opus 4.8):** Eingearbeitet — B1 (Task 11 Test-Reparatur), C1 (Task 12/Export-Cache gestrichen), C2 (Task-8-Abhängigkeit dokumentiert), C3 (Task 12 `processEvents`), C4 (eigener `ANALYZING`-String), T1 (Task 3 echter Capture-Test), O2 (Task 7 pyright non-blocking + gepinnt), N2 (Empty-State setzt `_colorbar=None`). Tasks 1, 2, 4, 5, 9 vom Review empirisch als korrekt bestätigt.
