# In-App-Anleitung mit Hilfe-Menü — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Eine umfangreiche, codebasierte Anleitung wird über ein neues Hilfe-Menü in der PySide6-Desktop-App aufrufbar, gespeist aus einer einzigen kanonischen Markdown-Datei (`ANLEITUNG_DESKTOP.md`).

**Architecture:** Eine kanonische Markdown-Datei dient als Single Source. Ein kleiner Ressourcen-Loader (`resources.py`) löst den Pfad in Dev- und PyInstaller-Frozen-Builds auf. Ein eigenständiger `ManualDialog` rendert den Markdown via `QTextBrowser.setMarkdown(...)`. `MainWindow` erhält eine Menüleiste mit Menü „Hilfe" → Aktion „Anleitung". Die Datei wird per PyInstaller-Spec mitgebündelt.

**Tech Stack:** Python 3.10+, PySide6 (Qt6), pytest, PyInstaller (Packaging). Qt headless via `QT_QPA_PLATFORM=offscreen` (vorhandene `tests/desktop/conftest.py`-Fixture `qapp`).

---

## File Structure

- **Create** `src/desktop/resources.py` — Pfad-/Textauflösung der Anleitung (dev vs. frozen). Eine Verantwortung: Ressourcenzugriff.
- **Create** `src/desktop/manual_dialog.py` — `ManualDialog(QDialog)`: rendert Markdown, Fehler-Fallback, Schließen-Button. Eine Verantwortung: Anleitungs-Anzeige.
- **Modify** `src/ui/strings.py` — neue Text-Konstanten (zentrale Benennung).
- **Modify** `src/desktop/main_window.py` — Menüleiste „Hilfe" → „Anleitung", `_show_manual`-Slot.
- **Rewrite** `ANLEITUNG_DESKTOP.md` — kanonische, umfangreiche Anleitung (Markdown).
- **Modify** `packaging/acc_viz.spec` — Anleitungsdatei in `datas`.
- **Modify** `pyproject.toml` + `README.md` — Version 0.3.0 → 0.4.0.
- **Create** `tests/desktop/test_resources.py`, `tests/desktop/test_manual_dialog.py` — neue Tests.
- **Modify** `tests/desktop/test_main_window.py` — Menü-Wiring-Tests.

Reihenfolge der Tasks: Strings → Loader → Dialog → MainWindow-Menü → Anleitungstext → Konsistenztest → Packaging → Version. Jede Task ist eigenständig grün.

---

### Task 1: Neue UI-Strings für Menü und Dialog

**Files:**
- Modify: `src/ui/strings.py`
- Test: `tests/ui/test_strings.py`

- [ ] **Step 1: Failing test schreiben**

In `tests/ui/test_strings.py` ans Ende anhängen:

```python
def test_manual_strings_present():
    from src.ui import strings as S

    assert S.MENU_HELP == "Hilfe"
    assert S.MENU_HELP_MANUAL == "Anleitung"
    assert S.MANUAL_DIALOG_TITLE
    assert S.MANUAL_LOAD_ERROR
```

- [ ] **Step 2: Test laufen lassen, Fehlschlag prüfen**

Run: `.venv/bin/python -m pytest tests/ui/test_strings.py::test_manual_strings_present -v`
Expected: FAIL mit `AttributeError: module 'src.ui.strings' has no attribute 'MENU_HELP'`

- [ ] **Step 3: Strings ergänzen**

Ans Ende von `src/ui/strings.py` anfügen:

```python

# --- Hilfe-Menü / Anleitungs-Dialog ---
MENU_HELP = "Hilfe"
MENU_HELP_MANUAL = "Anleitung"
MANUAL_DIALOG_TITLE = "Anleitung — Beschleunigungs-Visualisierung"
MANUAL_LOAD_ERROR = "Anleitung konnte nicht geladen werden."
```

- [ ] **Step 4: Test laufen lassen, Erfolg prüfen**

Run: `.venv/bin/python -m pytest tests/ui/test_strings.py::test_manual_strings_present -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/ui/strings.py tests/ui/test_strings.py
git commit -m "feat(strings): add Hilfe-Menü und Anleitungs-Dialog Texte"
```

---

### Task 2: Ressourcen-Loader für die Anleitungsdatei

**Files:**
- Create: `src/desktop/resources.py`
- Test: `tests/desktop/test_resources.py`

- [ ] **Step 1: Failing test schreiben**

Create `tests/desktop/test_resources.py`:

```python
from __future__ import annotations

from pathlib import Path

from src.desktop import resources


def test_manual_path_points_to_existing_file():
    path = resources.manual_path()
    assert isinstance(path, Path)
    assert path.name == "ANLEITUNG_DESKTOP.md"
    assert path.exists()


def test_load_manual_text_returns_nonempty():
    text = resources.load_manual_text()
    assert isinstance(text, str)
    assert text.strip()
```

- [ ] **Step 2: Test laufen lassen, Fehlschlag prüfen**

Run: `.venv/bin/python -m pytest tests/desktop/test_resources.py -v`
Expected: FAIL mit `ModuleNotFoundError: No module named 'src.desktop.resources'`

- [ ] **Step 3: Loader implementieren**

Create `src/desktop/resources.py`:

```python
from __future__ import annotations

"""Resource resolution for bundled data files (dev vs. PyInstaller frozen).

The manual lives as a single canonical Markdown file at the project root in dev
and is copied to the bundle root by the PyInstaller spec, where ``sys._MEIPASS``
points at the bundle directory.
"""

import sys
from pathlib import Path

_MANUAL_FILENAME = "ANLEITUNG_DESKTOP.md"


def _base_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(getattr(sys, "_MEIPASS"))
    # src/desktop/resources.py -> project root is parents[2].
    return Path(__file__).resolve().parents[2]


def manual_path() -> Path:
    """Absolute path to the canonical manual Markdown file."""
    return _base_dir() / _MANUAL_FILENAME


def load_manual_text() -> str:
    """Read the manual Markdown as UTF-8 text."""
    return manual_path().read_text(encoding="utf-8")
```

- [ ] **Step 4: Test laufen lassen, Erfolg prüfen**

Run: `.venv/bin/python -m pytest tests/desktop/test_resources.py -v`
Expected: PASS (beide Tests). Hinweis: `ANLEITUNG_DESKTOP.md` existiert bereits im Repo-Root, daher ist `path.exists()` schon jetzt wahr.

- [ ] **Step 5: Commit**

```bash
git add src/desktop/resources.py tests/desktop/test_resources.py
git commit -m "feat(desktop): add resource loader for bundled manual file"
```

---

### Task 3: ManualDialog (Markdown-Anzeige)

**Files:**
- Create: `src/desktop/manual_dialog.py`
- Test: `tests/desktop/test_manual_dialog.py`

- [ ] **Step 1: Failing test schreiben**

Create `tests/desktop/test_manual_dialog.py`:

```python
from __future__ import annotations

from src.desktop.manual_dialog import ManualDialog
from src.ui import strings as S


def test_dialog_renders_supplied_text(qapp):
    dialog = ManualDialog(text="# Überschrift\n\nEin Absatz.")
    assert dialog.windowTitle() == S.MANUAL_DIALOG_TITLE
    assert "Absatz" in dialog.browser.toPlainText()


def test_dialog_shows_fallback_on_load_error(qapp, monkeypatch):
    from src.desktop import manual_dialog as md

    def boom() -> str:
        raise OSError("missing")

    monkeypatch.setattr(md, "load_manual_text", boom)
    dialog = ManualDialog()
    assert dialog.browser.toPlainText().strip() == S.MANUAL_LOAD_ERROR
```

- [ ] **Step 2: Test laufen lassen, Fehlschlag prüfen**

Run: `.venv/bin/python -m pytest tests/desktop/test_manual_dialog.py -v`
Expected: FAIL mit `ModuleNotFoundError: No module named 'src.desktop.manual_dialog'`

- [ ] **Step 3: Dialog implementieren**

Create `src/desktop/manual_dialog.py`:

```python
from __future__ import annotations

"""Modal dialog rendering the application manual from Markdown.

Reads the canonical manual via :func:`src.desktop.resources.load_manual_text`
and renders it with ``QTextBrowser.setMarkdown``. On read failure it shows a
plain fallback message instead of crashing.
"""

from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QTextBrowser,
    QVBoxLayout,
    QWidget,
)

from src.desktop.resources import load_manual_text
from src.ui import strings as S


class ManualDialog(QDialog):
    """Scrollable, modal manual viewer."""

    def __init__(self, parent: QWidget | None = None, *, text: str | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle(S.MANUAL_DIALOG_TITLE)
        self.resize(760, 620)

        layout = QVBoxLayout(self)

        self.browser = QTextBrowser(self)
        self.browser.setOpenExternalLinks(True)
        layout.addWidget(self.browser)

        if text is None:
            try:
                text = load_manual_text()
            except OSError:
                text = None

        if text is None:
            self.browser.setPlainText(S.MANUAL_LOAD_ERROR)
        else:
            self.browser.setMarkdown(text)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close, self)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
```

Hinweis: Der Test patcht `src.desktop.manual_dialog.load_manual_text`, daher wird die Funktion modul-lokal importiert (wie oben) — kein Aufruf über `resources.load_manual_text`.

- [ ] **Step 4: Test laufen lassen, Erfolg prüfen**

Run: `.venv/bin/python -m pytest tests/desktop/test_manual_dialog.py -v`
Expected: PASS (beide Tests)

- [ ] **Step 5: Commit**

```bash
git add src/desktop/manual_dialog.py tests/desktop/test_manual_dialog.py
git commit -m "feat(desktop): add ManualDialog for in-app manual rendering"
```

---

### Task 4: Hilfe-Menü in MainWindow

**Files:**
- Modify: `src/desktop/main_window.py`
- Test: `tests/desktop/test_main_window.py`

- [ ] **Step 1: Failing test schreiben**

Ans Ende von `tests/desktop/test_main_window.py` anhängen:

```python
def test_help_menu_has_manual_action(qapp):
    from src.ui import strings as S

    win = MainWindow()
    menu_titles = [a.text() for a in win.menuBar().actions()]
    assert S.MENU_HELP in menu_titles
    assert win._manual_action.text() == S.MENU_HELP_MANUAL


def test_show_manual_opens_dialog(qapp, monkeypatch):
    from src.desktop import main_window as mw

    created = {}

    class FakeDialog:
        def __init__(self, parent):
            created["parent"] = parent

        def exec(self):
            created["exec"] = True
            return 0

    monkeypatch.setattr(mw, "ManualDialog", FakeDialog)
    win = MainWindow()
    win._manual_action.trigger()
    assert created.get("exec") is True
```

- [ ] **Step 2: Test laufen lassen, Fehlschlag prüfen**

Run: `.venv/bin/python -m pytest tests/desktop/test_main_window.py::test_help_menu_has_manual_action tests/desktop/test_main_window.py::test_show_manual_opens_dialog -v`
Expected: FAIL mit `AttributeError: 'MainWindow' object has no attribute '_manual_action'`

- [ ] **Step 3: Menü implementieren**

In `src/desktop/main_window.py` den Import um `ManualDialog` ergänzen. Bestehend:

```python
from src.desktop.export import prompt_export
```

ergänzen mit der Zeile direkt darunter:

```python
from src.desktop.manual_dialog import ManualDialog
```

Dann in `MainWindow.__init__`, direkt **nach** dem Toolbar-Block (nach `toolbar.addAction(self._export_action)`), einfügen:

```python

        # Menüleiste mit Hilfe-Menü.
        help_menu = self.menuBar().addMenu(S.MENU_HELP)
        self._manual_action = QAction(S.MENU_HELP_MANUAL, self)
        self._manual_action.triggered.connect(self._show_manual)
        help_menu.addAction(self._manual_action)
```

Und eine neue Methode hinzufügen, z. B. direkt nach der `_export`-Methode:

```python

    def _show_manual(self) -> None:
        """Open the modal manual dialog."""
        ManualDialog(self).exec()
```

`QAction` ist bereits importiert (`from PySide6.QtGui import QAction`).

- [ ] **Step 4: Test laufen lassen, Erfolg prüfen**

Run: `.venv/bin/python -m pytest tests/desktop/test_main_window.py -v`
Expected: PASS (alle Tests inkl. der bestehenden)

- [ ] **Step 5: Commit**

```bash
git add src/desktop/main_window.py tests/desktop/test_main_window.py
git commit -m "feat(desktop): add Hilfe menu opening the manual dialog"
```

---

### Task 5: Kanonische Anleitung schreiben

**Files:**
- Rewrite: `ANLEITUNG_DESKTOP.md`
- Test: `tests/desktop/test_resources.py` (Konsistenz-Marker ergänzen)

- [ ] **Step 1: Failing test schreiben (Konsistenzmarker)**

Ans Ende von `tests/desktop/test_resources.py` anhängen:

```python
def test_manual_contains_required_sections():
    text = resources.load_manual_text()
    for marker in (
        "Quick Guide",
        "Workflow",
        "Funktionsreferenz",
        "Frequenzband",
        "CSV exportieren",
    ):
        assert marker in text, marker
```

- [ ] **Step 2: Test laufen lassen, Fehlschlag prüfen**

Run: `.venv/bin/python -m pytest tests/desktop/test_resources.py::test_manual_contains_required_sections -v`
Expected: FAIL (aktuelle `ANLEITUNG_DESKTOP.md` enthält „Quick Guide"/„Funktionsreferenz" noch nicht — sie nutzt „Kurzanleitung").

- [ ] **Step 3: Anleitung neu schreiben**

`ANLEITUNG_DESKTOP.md` komplett ersetzen durch (Labels exakt aus `strings.py`/`control_panel.py`):

````markdown
# Beschleunigungs-Visualisierung — Desktop-App

Native PySide6/Qt-Anwendung zur Auswertung von **Beschleunigungs-PSD-Messungen
an Plattenbohrungen**. Für eine oder zwei Platten parallel berechnet das
Programm pro Bohrung den **Band-RMS** (Integration der PSD über ein wählbares
Frequenzband) und stellt ihn als Heatmap, Histogramm und PSD-Spektrum dar.

> Diese Anleitung ist auch in der App über **Hilfe → Anleitung** abrufbar.

## Quick Guide

1. **Starten** — `python3 desktop_main.py` (im Projektordner, mit aktiviertem `.venv`).
2. **Ordner wählen** — im linken Panel **„Einstellungen"** bei
   **„Platte 1 — Ordnerpfad"** über 📁 (**„Ordner wählen"**) oder per Pfadeingabe
   den Messordner setzen. **„Platte 2 — Ordnerpfad (optional)"** ist optional.
   Die Auswertung startet automatisch.
3. **Einstellungen anpassen** — jede Änderung aktualisiert die Anzeige sofort
   (siehe Funktionsreferenz).
4. **Spektrum ansehen** — in der Heatmap auf einen weißen Kreis (gemessene
   Bohrung) klicken; das PSD-Spektrum erscheint unterhalb der Platten.
5. **Exportieren** — in der Werkzeugleiste **„CSV exportieren"** klicken und den
   Speicherort wählen.

## Workflow

1. Pro Platte einen Ordner mit den Bohrungs-CSVs (und optional `Referenz.csv`)
   bereitstellen.
2. Platte 1 (und optional Platte 2) laden.
3. **Frequenzband (Hz)** und **Achse** für die gewünschte Auswertung setzen.
4. Für den direkten Vergleich zweier Platten **„Normalisiert (relativ zur
   Referenz)"** und **„Gemeinsame Farbskala"** aktivieren.
5. **Interpolation** und **Interpolations-Methode** nach Datenlage wählen.
6. Heatmap und Histogramm ablesen; bei Auffälligkeiten per Klick ins
   **Spektrum** einer Bohrung drillen.
7. Ergebnis über **„CSV exportieren"** sichern.

## Eingabedaten

Pro Platte ein Ordner mit:

- **Bohrungsmessungen**: CSV-Dateien `x{N}-y{M}.csv` (z. B. `x0-y3.csv`,
  case-insensitiv, 0-indizierte Koordinaten) mit den Spalten `Frequenz_Hz`,
  `PSD_X_g2Hz`, `PSD_Y_g2Hz`, `PSD_Z_g2Hz`.
- **Referenzmessung** (optional): `Referenz.csv` mit gleichem Schema —
  Voraussetzung für Normalisierung und Referenz-Stern.

## Funktionsreferenz

Bedienelemente im Panel **„Einstellungen"** (von oben nach unten):

- **Platte 1 — Ordnerpfad** / **Platte 2 — Ordnerpfad (optional)** — Messordner
  per 📁 **„Ordner wählen"** oder direkter Pfadeingabe. Platte 1 ist Pflicht,
  Platte 2 optional.
- **Frequenzband (Hz)** — Bereich `f_min`–`f_max` (0–25 000 Hz, Schrittweite
  100 Hz), über den der Band-RMS integriert wird. `f_min` bleibt stets
  mindestens 100 Hz kleiner als `f_max` (automatisch erzwungen). Wirkt auf
  Heatmap, Spektrum-Hervorhebung und CSV-Export.
- **Achse** — `X`, `Y`, `Z` einzeln oder `RSS` = √(gRMS_X² + gRMS_Y² + gRMS_Z²),
  die Root Sum of Squares der drei Achsen (richtungsunabhängige Gesamtbelastung).
- **Normalisiert (relativ zur Referenz)** — teilt jeden Bohrungs-RMS durch den
  Referenz-RMS derselben Platte; Ergebnis dimensionslos, Referenz = 1,0.
  Erfordert `Referenz.csv`.
- **Interpolation** — füllt fehlende Rasterzellen. Deaktiviert: nur gemessene
  Zellen werden angezeigt. Standard: aktiv.
- **Interpolations-Methode** — **„Linear (Delaunay)"** (schnell, zeigt
  Dreiecks-Facetten, bricht bei kollinearen Messpunkten ab) oder
  **„Thin-Plate-Spline"** (glatte Fläche, robust bei wenigen/kollinearen
  Punkten). Nur aktiv, wenn Interpolation eingeschaltet ist.
- **Histogramm-Bins** — Anzahl der Bins (5–50); wird automatisch auf die Anzahl
  gemessener Löcher reduziert, falls diese kleiner ist.
- **Statistik anzeigen** — blendet Mittelwert (µ), Median und ±1σ als Linien mit
  Zahlenwerten im Histogramm ein.
- **Gemeinsame Farbskala** — alle Heatmaps nutzen denselben zmin/zmax-Bereich
  (erleichtert den direkten Platten-Vergleich).
- **Farbskala** — Farbpalette der Heatmap. Viridis/Cividis sind perzeptuell
  gleichmäßig (empfohlen), RdBu betont Abweichungen.

Werkzeugleiste:

- **CSV exportieren** — schreibt pro Bohrung eine Zeile mit absolutem und
  normalisiertem Band-RMS für das aktuell gewählte Frequenzband und die Achse.
  Format: UTF-8 mit BOM, Semikolon-getrennt (Excel-kompatibel). Standardname
  `beschleunigung_export.csv`.

## Darstellung verstehen

- **Heatmap** (pro Platte) — räumliche Verteilung des Band-RMS über das
  Bohrungsraster (Achsen **x-Bohrung** / **y-Bohrung**). **Weiße Kreise**
  markieren gemessene Bohrungen (anklickbar fürs Spektrum), ein **gelber Stern**
  den Referenzwert in der Plattenmitte. Fehlende Zellen werden bei aktiver
  Interpolation gefüllt.
- **Histogramm** (pro Platte) — Verteilung der Bohrungswerte (Achse
  **Anzahl Löcher**), optional mit µ, Median und ±1σ.
- **Spektrum-Drilldown** — PSD über der Frequenz für die angeklickte Bohrung,
  inklusive Referenzkurve und hervorgehobenem Frequenzband; bei Achse `RSS`
  zusätzlich die Summenkurve X+Y+Z.
- **Referenz-Metrik** — pro Platte wird der Referenz-RMS im aktuellen
  Frequenzband angezeigt (bzw. „Normalisiert (Ref = 1.0)" im Normalisiert-Modus).

## Fehlermeldungen

Lade- und Datenfehler erscheinen in der Statusleiste bzw. als Hinweis im
Inhaltsbereich, u. a.:

- Pfad existiert nicht / Pfad ist kein Ordner.
- Ordner enthält keine Dateien im Format `x{N}-y{M}.csv`.
- CSV konnte nicht gelesen werden (Encoding/Trennzeichen unbekannt).
- Spalten fehlen (erwartet: `Frequenz_Hz, PSD_X_g2Hz, PSD_Y_g2Hz, PSD_Z_g2Hz`).
- Datei enthält keine auswertbaren Messwerte.

## Start & Entwicklung

- Desktop-App: `python3 desktop_main.py`
- Tests: `.venv/bin/python -m pytest`
- Native `.app`/`.exe` via PyInstaller: siehe [packaging/](packaging/).
````

- [ ] **Step 4: Test laufen lassen, Erfolg prüfen**

Run: `.venv/bin/python -m pytest tests/desktop/test_resources.py -v`
Expected: PASS (alle drei Tests)

- [ ] **Step 5: Commit**

```bash
git add ANLEITUNG_DESKTOP.md tests/desktop/test_resources.py
git commit -m "docs: rewrite ANLEITUNG_DESKTOP.md as canonical in-app manual"
```

---

### Task 6: Anleitung ins Packaging bündeln

**Files:**
- Modify: `packaging/acc_viz.spec`

- [ ] **Step 1: Spec anpassen**

In `packaging/acc_viz.spec` den `added_files`-Block ändern von:

```python
added_files = [
    (str(project_root / "desktop_main.py"), "."),
    (str(project_root / "src"), "src"),
]
```

zu:

```python
added_files = [
    (str(project_root / "desktop_main.py"), "."),
    (str(project_root / "src"), "src"),
    (str(project_root / "ANLEITUNG_DESKTOP.md"), "."),
]
```

- [ ] **Step 2: Syntax-Check der Spec**

Run: `.venv/bin/python -c "import ast; ast.parse(open('packaging/acc_viz.spec').read()); print('ok')"`
Expected: `ok`

- [ ] **Step 3: Verifizieren, dass der Loader-Pfad zum Bündelziel passt**

Run: `.venv/bin/python -m pytest tests/desktop/test_resources.py -v`
Expected: PASS. (Der frozen-Pfad `sys._MEIPASS / "ANLEITUNG_DESKTOP.md"` entspricht dem Bündelziel `"."` aus der Spec; im Dev-Lauf wird der Root-Pfad genutzt.)

- [ ] **Step 4: Commit**

```bash
git add packaging/acc_viz.spec
git commit -m "build(packaging): bundle ANLEITUNG_DESKTOP.md into frozen app"
```

---

### Task 7: Gesamtsuite grün + Versionsbump 0.4.0

**Files:**
- Modify: `pyproject.toml`, `README.md`

- [ ] **Step 1: Volle Testsuite laufen lassen**

Run: `.venv/bin/python -m pytest`
Expected: PASS (alle Tests, inkl. der neuen). Bei Fehlern beheben, bevor weiter.

- [ ] **Step 2: Version in `pyproject.toml` bumpen**

In `pyproject.toml` ändern:

```python
version = "0.3.0"
```

zu:

```python
version = "0.4.0"
```

- [ ] **Step 3: README-Badge bumpen**

In `README.md` Zeile 1 ändern von:

```markdown
![version](https://img.shields.io/badge/version-0.3.0-blue)
```

zu:

```markdown
![version](https://img.shields.io/badge/version-0.4.0-blue)
```

- [ ] **Step 4: Konsistenz prüfen**

Run: `grep -rn "0\.4\.0" pyproject.toml README.md && git tag -l v0.4.0`
Expected: zwei Treffer (pyproject, README); `git tag -l v0.4.0` liefert **keine** Ausgabe (Tag existiert noch nicht).

- [ ] **Step 5: Commit + Tag + Push**

```bash
git add pyproject.toml README.md
git commit -m "chore: bump version to 0.4.0"
git tag -a v0.4.0 -m "v0.4.0"
git push --follow-tags
```

---

## Self-Review

**Spec coverage:**
- Hilfe-Menü → Task 4. In-App-Dialog aus Markdown → Task 3. Ressourcen-Loader (dev/frozen) → Task 2. Kanonische Datei ersetzt `ANLEITUNG_DESKTOP.md` → Task 5. Neue Strings → Task 1. Packaging → Task 6. Versionsbump 0.4.0 → Task 7. Tests (Loader/Dialog/Menü/Konsistenz) → Tasks 2–5. Alle Spec-Abschnitte abgedeckt.

**Placeholder scan:** Keine TBD/TODO; alle Code- und Textblöcke vollständig ausformuliert.

**Type/Name consistency:** `MENU_HELP`, `MENU_HELP_MANUAL`, `MANUAL_DIALOG_TITLE`, `MANUAL_LOAD_ERROR` einheitlich über Tasks 1/3/4. `ManualDialog(parent, *, text=None)`, `.browser`, `.exec()` konsistent zwischen Task 3 (Definition) und Task 4 (Mock). `resources.manual_path()`/`load_manual_text()` konsistent zwischen Task 2 (Definition), Task 3 (modul-lokaler Import für Patchbarkeit) und Task 5 (Konsistenztest).

**Hinweis Task 4 Test:** `win.menuBar().actions()` liefert die Top-Level-Menüs; deren `.text()` enthält den Menütitel — robust gegenüber Qt-Interna.
