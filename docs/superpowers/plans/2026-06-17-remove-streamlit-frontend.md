# Streamlit-Frontend entfernen (Desktop-only) — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Das Streamlit-Frontend vollständig und rückstandsfrei entfernen; übrig bleibt die reine PySide6-Desktop-App.

**Architecture:** `src/ui/` (Streamlit) wird aufgelöst. Die beiden geteilten Module `strings.py` + `errors.py` wandern nach `src/core/` (da `src/core/pipeline.py` sie importiert und `core` nicht von `desktop` abhängen darf). Alle reinen Streamlit-Module, `app.py`, die Streamlit-Tests, die `streamlit`/`plotly`-Dependencies sowie sämtliche Streamlit/Plotly-Verweise in Code, Docstrings und Doku werden entfernt.

**Tech Stack:** Python 3.10+, PySide6, matplotlib, pandas/numpy/scipy, pytest, pyright.

**Testing-Strategie (wichtig):** Dies ist ein Refactor/Entfernung, kein Feature. Die **bestehende Testsuite** ist das Regressions-Sicherheitsnetz, und der **repo-weite grep-Gate** (Task 6) ist der Akzeptanztest für „keine Rückstände". Jede Task endet mit `pytest` grün. TDD-„erst-failing-Test" entfällt hier bewusst — es wird kein neues Verhalten gebaut, sondern Verhalten unter Test verschoben/entfernt.

**Definition of Done (gesamt):**
- `src/ui/` existiert nicht mehr
- `python3 -m pytest` grün
- `pyright` 0 Fehler
- `python3 desktop_main.py` startet
- grep-Gate (Task 6) liefert außerhalb `docs/superpowers/` **null** Treffer für `streamlit|plotly|src\.ui|src/ui|app\.py`
- Version 0.5.0 in `pyproject.toml` + README-Badge, Tag `v0.5.0` gepusht

---

## Task 1: Geteilten Code nach `src/core/` verschieben + Importe rewiren

Atomarer Schritt: Verschieben **und** alle Importe in einem Commit, damit die Suite grün bleibt.

**Files:**
- Move: `src/ui/strings.py` → `src/core/strings.py`
- Move: `src/ui/errors.py` → `src/core/errors.py`
- Move: `tests/ui/test_strings.py` → `tests/core/test_strings.py`
- Move: `tests/ui/test_errors.py` → `tests/core/test_errors.py`
- Modify: `src/core/errors.py` (interner Import)
- Modify: `src/core/pipeline.py:26-27`
- Modify: `src/desktop/main_window.py:40`
- Modify: `src/desktop/control_panel.py:32`
- Modify: `src/desktop/manual_dialog.py:23`
- Modify: `src/desktop/export.py:13`
- Modify: `src/desktop/plots/spectrum_canvas.py:19`
- Modify: `src/desktop/plots/heatmap_canvas.py:20`
- Modify: `src/desktop/plots/histogram_canvas.py:14`
- Modify: `tests/desktop/test_main_window.py:42` (Consumer von `strings`)
- Modify: `tests/desktop/test_manual_dialog.py:4` und `:25` (Consumer von `strings`)

- [ ] **Step 1: Module per `git mv` verschieben**

```bash
git mv src/ui/strings.py src/core/strings.py
git mv src/ui/errors.py src/core/errors.py
git mv tests/ui/test_strings.py tests/core/test_strings.py
git mv tests/ui/test_errors.py tests/core/test_errors.py
```

- [ ] **Step 2: Internen Import in `src/core/errors.py` anpassen**

Ändere die Importzeile (war `from src.ui import strings as S`):

```python
from src.core import strings as S
```

- [ ] **Step 3: Importe in den 8 Consumer-Dateien anpassen**

In `src/core/pipeline.py` (Zeilen 26-27) ersetzen:

```python
from src.core import strings as S
from src.core.errors import format_error
```

In jeder dieser Dateien die Zeile `from src.ui import strings as S` ersetzen durch `from src.core import strings as S`:
- `src/desktop/main_window.py`
- `src/desktop/control_panel.py`
- `src/desktop/manual_dialog.py`
- `src/desktop/export.py`
- `src/desktop/plots/spectrum_canvas.py`
- `src/desktop/plots/heatmap_canvas.py`
- `src/desktop/plots/histogram_canvas.py`

- [ ] **Step 4: Importe in den verschobenen Tests anpassen**

In `tests/core/test_strings.py` beide Vorkommen (Zeile 2 und im Funktionskörper ~Zeile 35) ersetzen:

```python
from src.core import strings as S
```

In `tests/core/test_errors.py` (war `from src.ui.errors import format_error`):

```python
from src.core.errors import format_error
```

- [ ] **Step 4b: `strings`-Importe in `tests/desktop/` anpassen (sonst bricht die Suite nach Task 2)**

`tests/desktop/test_main_window.py` (Zeile 42) und `tests/desktop/test_manual_dialog.py` (Zeile 4 **und** Zeile 25) — jeweils `from src.ui import strings as S` ersetzen durch:

```python
from src.core import strings as S
```

- [ ] **Step 5: Sicherstellen, dass `strings`/`errors` vollständig migriert sind**

Run: `grep -rn "from src.ui import strings\|from src\.ui\.errors\|src\.ui\.strings\|src\.ui\.errors" src tests`
Expected: **keine Treffer**

(Hinweis: `src.ui.sidebar` / `src.ui.export` werden hier noch von zwei Backward-compat-Tests referenziert — die existieren bis Task 2 legitim weiter und werden dort entfernt. Deshalb hier **kein** pauschales `grep src.ui`.)

- [ ] **Step 6: Volle Testsuite laufen lassen**

Run: `python3 -m pytest -q`
Expected: PASS (alle Tests grün, inkl. der nach `tests/core/` verschobenen)

- [ ] **Step 7: Commit**

```bash
git add -A
git commit -m "refactor(core): move shared strings/errors from ui to core"
```

---

## Task 2: Reine Streamlit-Module, `app.py` und Streamlit-Tests löschen

**Files:**
- Delete: `app.py`
- Delete: `src/ui/sidebar.py`, `src/ui/heatmap.py`, `src/ui/histogram.py`, `src/ui/spectrum.py`, `src/ui/export.py`, `src/ui/__init__.py`
- Delete: `tests/ui/test_sidebar.py`, `tests/ui/test_heatmap.py`, `tests/ui/test_histogram.py`, `tests/ui/test_smoke.py`, `tests/ui/test_export.py`, `tests/ui/conftest.py`, `tests/ui/__init__.py`
- Modify: `tests/desktop/test_export.py` (obsoleten Re-Export-Test entfernen)
- Modify: `tests/core/test_settings.py` (obsoleten Sidebar-Re-Export-Test entfernen)
- Modify: `pyrightconfig.json` (`app.py` aus `include` entfernen)

- [ ] **Step 1: Streamlit-Quellmodule + Entry + Shim löschen**

`src/ui/strings.py` ist nach Task 1 ein temporärer Backward-compat-Shim (Re-Export aus `src.core.strings`), der nur die hier gelöschten Streamlit-Module am Leben hielt — er muss mit weg. Die kanonischen `strings.py`/`errors.py` liegen bereits in `src/core/`, daher kann das **gesamte** `src/ui/`-Verzeichnis entfernt werden:

```bash
git rm app.py \
  src/ui/sidebar.py src/ui/heatmap.py src/ui/histogram.py \
  src/ui/spectrum.py src/ui/export.py src/ui/strings.py src/ui/__init__.py
```

- [ ] **Step 2: Streamlit-Tests + ui-Test-Infrastruktur löschen**

```bash
git rm tests/ui/test_sidebar.py tests/ui/test_heatmap.py \
  tests/ui/test_histogram.py tests/ui/test_smoke.py tests/ui/test_export.py \
  tests/ui/conftest.py tests/ui/__init__.py
```

- [ ] **Step 2b: Obsolete Backward-compat-Tests entfernen (referenzieren jetzt gelöschte `src.ui`-Module)**

In `tests/desktop/test_export.py` diese Funktion **komplett** löschen (sie prüfte nur den nicht mehr existierenden Re-Export):

```python
def test_core_export_module_reexported_from_ui():
    from src.ui.export import build_export_dataframe as ui_fn

    assert ui_fn is build_export_dataframe
```

In `tests/core/test_settings.py` diese Funktion **komplett** löschen:

```python
def test_sidebar_reexports_core_settings():
    """Backward-compat: src.ui.sidebar must still expose the same Settings/Axis."""
    from src.ui.sidebar import Axis as SidebarAxis
    from src.ui.sidebar import Settings as SidebarSettings

    assert SidebarSettings is Settings
    assert SidebarAxis is Axis
```

(Der Rest beider Dateien bleibt unverändert. Falls `build_export_dataframe` dadurch in `test_export.py` ungenutzt wird: Import-Zeile prüfen — sie wird von `test_export_dataframe_*`-Tests weiter gebraucht, also stehen lassen.)

- [ ] **Step 2c: `app.py` aus `pyrightconfig.json` entfernen (Datei wird gelöscht)**

In `pyrightconfig.json` (Zeile 3) den `include`-Eintrag anpassen:

Alt:
```json
  "include": ["src", "tests", "app.py", "packaging"],
```
Neu:
```json
  "include": ["src", "tests", "packaging"],
```

- [ ] **Step 3: Bestätigen, dass die Verzeichnisse weg sind**

Run: `ls src/ui tests/ui 2>&1`
Expected: „No such file or directory" für beide (leere Verzeichnisse von `git rm` entfernt; falls noch vorhanden, mit `rmdir src/ui tests/ui` leeren)

- [ ] **Step 4: Vollständiger `src.ui`-Gate (jetzt müssen alle Referenzen weg sein)**

Run: `grep -rn "src\.ui\|src/ui" src tests`
Expected: **keine Treffer** (sidebar/export-Re-Export-Tests entfernt, Module gelöscht)

- [ ] **Step 5: Testsuite + pyright grün**

Run: `python3 -m pytest -q && pyright`
Expected: pytest PASS (kein Import-/Collection-Fehler), pyright 0 errors (kein fehlender `app.py`-Include mehr)

- [ ] **Step 6: Commit**

```bash
git add -A
git commit -m "refactor: delete Streamlit frontend modules, entry and tests"
```

---

## Task 3: Streamlit/Plotly-Dependencies entfernen

**Files:**
- Modify: `requirements.txt`
- Modify: `pyproject.toml:17-18`
- Modify: `packaging/acc_viz.spec:38-48`
- Modify: `.gitignore:4` (`.streamlit/`-Eintrag entfernen)

- [ ] **Step 1: `requirements.txt` — Legacy-Block entfernen**

Entferne diese letzten Zeilen vollständig:

```
# --- legacy Streamlit frontend (app.py); kept until the desktop port is
#     verified against real data. Not bundled into the native .exe/.app. ---
streamlit>=1.35.0
plotly>=5.18.0
```

- [ ] **Step 2: `pyproject.toml` — `web`-Extra streichen**

Entferne diese Zeile aus `[project.optional-dependencies]`:

```toml
web = ["streamlit>=1.35.0", "plotly>=5.18.0"]
```

- [ ] **Step 3: `packaging/acc_viz.spec` — Excludes bereinigen**

Ersetze den Kommentar + die `excludes`-Liste. Vorher:

```python
# Keep the bundle lean: the native app never imports the old web stack.
excludes = [
    "streamlit",
    "plotly",
    "tornado",
    "tkinter",
    "PyQt5",
    "PyQt6",
    "IPython",
]
```

Nachher (Streamlit/Plotly-Einträge **und** der „old web stack"-Hinweis entfernt):

```python
# Keep the bundle lean: exclude GUI/server stacks the native app never imports.
excludes = [
    "tornado",
    "tkinter",
    "PyQt5",
    "PyQt6",
    "IPython",
]
```

- [ ] **Step 3b: `.gitignore` — `.streamlit/`-Eintrag entfernen**

Lösche in `.gitignore` (Zeile 4) die Zeile:

```
.streamlit/
```

- [ ] **Step 4: Gegencheck Dependencies + Config**

Run: `grep -rn "streamlit\|plotly" requirements.txt pyproject.toml packaging/ .gitignore`
Expected: **keine Treffer**

- [ ] **Step 5: Commit**

```bash
git add requirements.txt pyproject.toml packaging/acc_viz.spec .gitignore
git commit -m "build: drop streamlit/plotly dependencies and config residue"
```

---

## Task 4: Streamlit/Plotly-Verweise in aktiven Quell-Docstrings/Kommentaren scrubben

Rein redaktionell (Docstrings/Kommentare). Keine Logikänderung. Nach jedem Edit bleibt die Suite grün, daher ein Commit am Ende.

**Files (Modify):**
`desktop_main.py`, `src/core/pipeline.py`, `src/core/export.py`, `src/core/colorscales.py`, `src/core/settings.py`, `src/desktop/control_panel.py`, `src/desktop/main_window.py`, `src/desktop/export.py`, `src/desktop/plots/heatmap_canvas.py`, `src/desktop/plots/spectrum_canvas.py`, `src/desktop/plots/histogram_canvas.py`, `src/platform_utils/folder_picker.py`, `packaging/entry.py`

- [ ] **Step 1: `desktop_main.py`** — Zeilen 5-6

Alt:
```
Run with ``python desktop_main.py``. This replaces the Streamlit web app
(``app.py``) for the packaged, native desktop build.
```
Neu:
```
Run with ``python desktop_main.py``. This is the entry point for the
packaged, native desktop build.
```

- [ ] **Step 2: `src/core/pipeline.py`** — Modul-Docstring 5-7

Alt:
```
Extracted from the original Streamlit ``app.py`` so the exact same computation
can drive any frontend (Streamlit, Qt) and be unit-tested without a UI. No
Streamlit / Qt imports here on purpose.
```
Neu:
```
Frontend-agnostic computation core: the same logic drives the Qt desktop UI
and can be unit-tested without a UI. No Qt imports here on purpose.
```

- [ ] **Step 3: `src/core/pipeline.py`** — Docstring `load_plates` (Zeile 117)

Alt:
```
    Mirrors the original Streamlit load loop: each folder is loaded (with
```
Neu:
```
    Each folder is loaded (with
```

- [ ] **Step 4: `src/core/pipeline.py`** — Docstring `analyze` (Zeile 155)

Alt:
```
    Mirrors the original Streamlit compute block exactly.

    Args:
```
Neu:
```
    Args:
```

- [ ] **Step 4b: `src/core/pipeline.py`** — Kommentar Zeile 79 (`st.cache_data`-Hinweis)

Alt:
```
# --- loading (with mtime-based caching, replacing st.cache_data) -----------
```
Neu:
```
# --- loading (with mtime-based caching) ------------------------------------
```

- [ ] **Step 5: `src/core/export.py`** — Modul-Docstring 5-7

Alt:
```
Extracted from the original Streamlit ``src.ui.export`` so the same export logic
can drive any frontend (Streamlit download button, Qt save dialog). No Streamlit
import here on purpose.
```
Neu:
```
Kept frontend-agnostic so the export logic backs the Qt save dialog and can be
unit-tested without a UI.
```

- [ ] **Step 6: `src/core/export.py`** — Zeile 89

Alt:
```
    in German locales (matching the original Streamlit download).
```
Neu:
```
    in German locales.
```

- [ ] **Step 6b: `src/desktop/export.py`** — Modul-Docstring Zeilen 5-6

Alt:
```
Reuses the frontend-agnostic :func:`src.core.export.export_csv_bytes`, so the
exported file is byte-for-byte identical to the Streamlit download.
```
Neu:
```
Reuses the frontend-agnostic :func:`src.core.export.export_csv_bytes` for the
actual byte encoding.
```

- [ ] **Step 7: `src/core/colorscales.py`** — Modul-Docstring 5-7

Alt:
```
Single source of truth shared by the Streamlit sidebar, the Qt control panel
and the matplotlib heatmap canvas, so the selectable list and the Plotly→mpl
mapping can never drift apart.
```
Neu:
```
Single source of truth shared by the Qt control panel and the matplotlib
heatmap canvas, so the selectable list and the colormap mapping can never
drift apart.
```

- [ ] **Step 8: `src/core/colorscales.py`** — Kommentar 10-11

Alt:
```
# User-selectable colorscale identifiers (Plotly naming, kept for continuity
# with the original Streamlit app and any saved user expectations).
```
Neu:
```
# User-selectable colorscale identifiers, kept stable for continuity with
# saved user expectations.
```

- [ ] **Step 9: `src/core/settings.py`** — Zeile 5

Alt:
```
This module is intentionally free of any frontend dependency (no Streamlit, no
```
Neu:
```
This module is intentionally free of any frontend dependency (no Qt, no
```
(Hinweis: Zeile 6 enthält voraussichtlich „Qt, …". Datei bei der Bearbeitung kurz lesen und sicherstellen, dass der Satz grammatikalisch glatt bleibt und kein „Streamlit" mehr vorkommt.)

- [ ] **Step 10: `src/desktop/control_panel.py`** — Docstring 3-5

Alt:
```
"""Native PySide6 settings panel — the desktop replacement for the Streamlit sidebar.

Mirrors :func:`src.ui.sidebar.render_sidebar`: it exposes the same controls and
```
Neu:
```
"""Native PySide6 settings panel for the application.

It exposes the analysis controls and
```

- [ ] **Step 11: `src/desktop/main_window.py`** — Docstring 3 + 7

Alt (Zeile 3):
```
"""Main application window — native desktop replacement for the Streamlit app.
```
Neu:
```
"""Main application window for the native desktop app.
```

Alt (Zeilen 7-8):
```
pipeline and redrawing. This replaces Streamlit's "re-run the whole script on
every widget change" model with an explicit Qt signal/slot recompute.
```
Neu:
```
pipeline and redrawing — an explicit Qt signal/slot recompute on every
control change.
```

- [ ] **Step 12: `src/desktop/main_window.py`** — Zeile 229

Alt:
```
        # Reference metric (mirrors st.metric in the Streamlit app).
```
Neu:
```
        # Reference metric.
```

- [ ] **Step 13: `src/desktop/plots/heatmap_canvas.py`** — Docstring 3-9

Alt:
```
"""Native matplotlib heatmap canvas — the desktop replacement for the Plotly heatmap.

Mirrors :func:`src.ui.heatmap.make_heatmap`: an interpolated grid drawn with the
selected colormap, white markers at measured holes and an optional yellow star at
the plate center for the reference value. Clicking a cell emits
:attr:`HeatmapCanvas.holeClicked` with the snapped integer ``(x, y)`` coordinate,
replacing Streamlit's ``st.plotly_chart(on_select="rerun")``.
"""
```
Neu:
```
"""Native matplotlib heatmap canvas for the application.

An interpolated grid drawn with the selected colormap, white markers at measured
holes and an optional yellow star at the plate center for the reference value.
Clicking a cell emits :attr:`HeatmapCanvas.holeClicked` with the snapped integer
``(x, y)`` coordinate.
"""
```

- [ ] **Step 14: `src/desktop/plots/heatmap_canvas.py`** — Zeilen 88-89

Alt:
```
    NaN/gap cells and positions outside the grid return ``None`` (Plotly parity
    with ``hoverongaps=False``).
```
Neu:
```
    NaN/gap cells and positions outside the grid return ``None``.
```

- [ ] **Step 15: `src/desktop/plots/heatmap_canvas.py`** — Zeile 195

Alt:
```
        # origin="upper" puts y=0 at the top, matching the Plotly reversed y-axis.
```
Neu:
```
        # origin="upper" puts y=0 at the top (reversed y-axis).
```

- [ ] **Step 16: `src/desktop/plots/spectrum_canvas.py`** — Docstring 3-5

Alt:
```
"""Native matplotlib PSD spectrum canvas — desktop replacement for the Plotly spectrum.

Mirrors :func:`src.ui.spectrum.render_spectrum`: a log-scaled PSD plot for one
```
Neu:
```
"""Native matplotlib PSD spectrum canvas for the application.

A log-scaled PSD plot for one
```

- [ ] **Step 17: `src/desktop/plots/histogram_canvas.py`** — Docstring 3-5

Alt:
```
"""Native matplotlib histogram canvas — desktop replacement for the Plotly histogram.

Mirrors :func:`src.ui.histogram.make_histogram`: non-finite values are dropped,
```
Neu:
```
"""Native matplotlib histogram canvas for the application.

Non-finite values are dropped,
```

- [ ] **Step 18: `src/desktop/plots/histogram_canvas.py`** — Zeile 46

Alt:
```
        """Draw the histogram. Mirrors ``make_histogram`` semantics."""
```
Neu:
```
        """Draw the histogram."""
```

- [ ] **Step 19: `src/platform_utils/folder_picker.py`** — Zeile 3 + Kommentar 68

Alt (Zeile 3):
```
"""Cross-platform native folder-picker dialog for Streamlit worker threads."""
```
Neu:
```
"""Cross-platform native folder-picker dialog run on a worker thread."""
```

Alt (Zeilen 68-69, Kommentar):
```
    # Tk() must be created on the thread that owns it. Streamlit runs user code
    # on worker threads, so spawn a dedicated thread and hand the result back
```
Neu:
```
    # Tk() must be created on the thread that owns it, so spawn a dedicated
    # thread and hand the result back
```

- [ ] **Step 19b: `packaging/entry.py`** — Modul-Docstring Zeile 5 (`former Streamlit bootstrap`)

Alt:
```
Replaces the former Streamlit bootstrap. When ``ACC_VIZ_SMOKE=1`` the app quits
itself after a short delay so the packaging smoke test can assert a clean exit
```
Neu:
```
When ``ACC_VIZ_SMOKE=1`` the app quits
itself after a short delay so the packaging smoke test can assert a clean exit
```

- [ ] **Step 20: Gegencheck — keine Streamlit/Plotly-Verweise mehr im aktiven Code**

Run:
```bash
grep -rn "Streamlit\|streamlit\|Plotly\|plotly\|src\.ui\|src/ui\|app\.py\|st\.metric\|st\.plotly_chart\|st\.cache_data\|st\.session_state\|render_sidebar\|make_heatmap\|make_histogram\|render_spectrum" \
  src/ desktop_main.py packaging/entry.py packaging/build.py
```
Expected: **keine Treffer**

- [ ] **Step 21: Testsuite + pyright grün**

Run: `python3 -m pytest -q && pyright`
Expected: pytest PASS, pyright 0 errors

- [ ] **Step 22: Commit**

```bash
git add -A
git commit -m "docs: scrub Streamlit/Plotly references from active source"
```

---

## Task 5: README + BESCHREIBUNG.md auf Desktop-only umschreiben

**Files:**
- Modify: `README.md:20-24`
- Modify: `BESCHREIBUNG.md` (mehrere Stellen)

- [ ] **Step 1: `README.md` — Streamlit-Start-Abschnitt entfernen**

Entferne diesen Block vollständig (Zeilen 20-24):

```
**Streamlit-App (Legacy-Frontend):**

```bash
python3 -m streamlit run app.py
```

```

So bleibt unter „## Start" nur noch der Desktop-Block übrig:

```
## Start

**Desktop-App (PySide6, nativ):**

```bash
python3 desktop_main.py
```

## Entwicklung
```

- [ ] **Step 2: `BESCHREIBUNG.md` — Einleitung (Zeilen 3-4)**

Alt:
```
Streamlit-App zur Auswertung und Visualisierung von Beschleunigungs-PSD-Messungen
an Plattenbohrungen.
```
Neu:
```
Desktop-App (PySide6) zur Auswertung und Visualisierung von
Beschleunigungs-PSD-Messungen an Plattenbohrungen.
```

- [ ] **Step 3: `BESCHREIBUNG.md` — Zeile 12 (Sidebar → Bedienpanel)**

Alt:
```
- **UI-Einstellungen** (Sidebar):
```
Neu:
```
- **UI-Einstellungen** (Bedienpanel):
```

- [ ] **Step 4: `BESCHREIBUNG.md` — Zeile 18 (Plotly-Farbpalette)**

Alt:
```
  - Plotly-Farbpalette
```
Neu:
```
  - Farbskala
```

- [ ] **Step 5: `BESCHREIBUNG.md` — Zeilen 30-31 (Plotly-Heatmap)**

Alt:
```
6. **Heatmap-Anzeige**: pro Platte eine Plotly-Heatmap mit
   Lochmarkern und Referenz-Stern in Plattenmitte.
```
Neu:
```
6. **Heatmap-Anzeige**: pro Platte eine matplotlib-Heatmap mit
   Lochmarkern und Referenz-Stern in Plattenmitte.
```

- [ ] **Step 6: `BESCHREIBUNG.md` — Zeile 36 (Output, „interaktiv, Plotly")**

Alt:
```
- **Heatmaps** der Band-RMS-Verteilung pro Platte (interaktiv, Plotly).
```
Neu:
```
- **Heatmaps** der Band-RMS-Verteilung pro Platte (matplotlib).
```

- [ ] **Step 7: `BESCHREIBUNG.md` — Start-Befehl (Zeilen 44-46)**

Alt:
```
```bash
python3 -m streamlit run app.py
```
```
Neu:
```
```bash
python3 desktop_main.py
```
```

- [ ] **Step 8: Commit**

```bash
git add README.md BESCHREIBUNG.md
git commit -m "docs: rewrite README/BESCHREIBUNG for desktop-only app"
```

---

## Task 6: Verifikation + Version-Bump auf 0.5.0

**Files:**
- Modify: `pyproject.toml:7`
- Modify: `README.md:1`

- [ ] **Step 1: Repo-weiter grep-Gate (Akzeptanztest „keine Rückstände")**

Run:
```bash
grep -rIn \
  -e streamlit -e Streamlit -e plotly -e Plotly \
  -e 'src\.ui' -e 'src/ui' -e 'app\.py' \
  -e 'st\.cache_data' -e 'st\.metric' -e 'st\.plotly_chart' -e 'st\.session_state' \
  . \
  --exclude-dir=.git --exclude-dir=superpowers --exclude-dir=node_modules \
  --exclude-dir=.pytest_cache --exclude-dir='*.egg-info'
```
Expected: **null Treffer**. `--exclude-dir=superpowers` schließt **gezielt nur** die History (`docs/superpowers/`) aus — eine Streamlit-Erwähnung in irgendeiner anderen Doc-Datei würde weiterhin gefunden. Jeder Treffer außerhalb der History muss behoben werden, bevor es weitergeht.

Zusätzlicher Egg-Info-Check (generierte Metadaten dürfen ebenfalls keine Streamlit-Spur tragen):
```bash
grep -rIn "streamlit\|plotly\|app\.py\|src/ui" acc_visualisation.egg-info 2>/dev/null || echo "egg-info clean"
```
Falls `acc_visualisation.egg-info/SOURCES.txt` o.ä. noch alte Pfade listet: das ist generiert — mit `python3 -m pip install -e . 2>/dev/null` oder Löschen des `*.egg-info`-Ordners neu erzeugen; nicht von Hand editieren.

- [ ] **Step 2: Volle Testsuite grün**

Run: `python3 -m pytest -q`
Expected: PASS, 0 failures/errors

- [ ] **Step 3: pyright sauber**

Run: `pyright`
Expected: 0 errors, 0 warnings

- [ ] **Step 4: Desktop-App startet**

Run: `python3 desktop_main.py` (kurz starten, Fenster erscheint, dann schließen)
Expected: App-Fenster öffnet ohne Traceback. (Headless/CI: stattdessen `python3 -c "import src.desktop.main_window"` als Import-Smoke.)

- [ ] **Step 5: Version-Konsistenzcheck vor Bump**

Run: `grep -n "version" pyproject.toml; sed -n '1p' README.md; git tag | grep v0.5.0 || echo "kein v0.5.0-Tag"`
Expected: pyproject `0.4.0`, Badge `0.4.0`, **kein** `v0.5.0`-Tag

- [ ] **Step 6: Version auf 0.5.0 bumpen**

In `pyproject.toml` (Zeile 7):
```toml
version = "0.5.0"
```

In `README.md` (Zeile 1):
```
![version](https://img.shields.io/badge/version-0.5.0-blue)
```

- [ ] **Step 7: Bump committen**

```bash
git add pyproject.toml README.md
git commit -m "chore: bump version to 0.5.0"
```

- [ ] **Step 8: Annotated Tag + Push (mit Tag)**

```bash
git tag -a v0.5.0 -m "v0.5.0"
git push --follow-tags
```
Expected: Commit + Tag `v0.5.0` landen auf dem Remote.

---

## Self-Review (vom Plan-Autor durchgeführt)

**Spec-Coverage:** Spec-Abschnitte A–E + Verifikation + Versionierung sind abgedeckt — A→Task 2, B→Task 1, C→Task 1, D→Task 3, E→Task 4+5, Verifikation→Task 6, Versionierung→Task 6. ✓

**Placeholder-Scan:** Keine „TBD/TODO/später". Jeder Edit-Step zeigt exakten Alt→Neu-Text; jeder Test-Step zeigt Befehl + erwartete Ausgabe. ✓ (Einzige Lese-Anweisung: Task 4 Step 9 `settings.py` Zeile 6 — bewusst, da die Folgezeile nicht im Kontext erfasst ist; Zielzustand „kein Streamlit, grammatikalisch glatt" ist eindeutig.)

**Typ-/Namens-Konsistenz:** Importpfade `src.core.strings` / `src.core.errors` durchgängig identisch in Task 1 verwendet (Quelle, Consumer, Tests). Keine widersprüchlichen Symbolnamen. ✓

## Härtung nach adversarialem grill-me (2026-06-17)

Ein Subagent hat den Plan gegen den echten Code zerlegt; alle Befunde verifiziert und eingearbeitet:

- **B1** — `tests/desktop/test_main_window.py:42`, `tests/desktop/test_manual_dialog.py:4,25` importieren `strings` → in Task 1 Step 4b ergänzt (sonst Collection-Error nach Task 2).
- **B2** — Backward-compat-Tests `test_core_export_module_reexported_from_ui` (`tests/desktop/test_export.py`) und `test_sidebar_reexports_core_settings` (`tests/core/test_settings.py`) referenzieren gelöschte `src.ui`-Module → in Task 2 Step 2b entfernt.
- **B3** — `src/desktop/export.py:6` „Streamlit download" → Task 4 Step 6b.
- **B4** — `src/core/pipeline.py:79` `st.cache_data`-Kommentar → Task 4 Step 4b.
- **B5** — `packaging/entry.py:5` „former Streamlit bootstrap" → Task 4 Step 19b.
- **Q1** — `pyrightconfig.json:3` listet `app.py` → Task 2 Step 2c entfernt es (sonst pyright-Fehler).
- **Q2** — `.gitignore:4` `.streamlit/` → Task 3 Step 3b entfernt es.
- Gate-Verschärfung: Task 1 Step 5 prüft nur noch `strings`/`errors`-Migration (sidebar/export-Refs leben bis Task 2 legitim weiter); Task 2 Step 4 macht den vollständigen `src.ui`-Gate; Task 4 Step 20 + Task 6 Step 1 fangen zusätzlich `st.`-API-Muster und schließen die History gezielt via `--exclude-dir=superpowers` aus.
