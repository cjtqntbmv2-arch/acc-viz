# Design: In-App-Anleitung mit Hilfe-Menü (Desktop-App)

**Datum:** 2026-06-16
**Status:** Genehmigt (Brainstorming)
**Betrifft:** PySide6-Desktop-App (`src/desktop/`)

## Ziel

Eine umfangreiche, codebasierte Anleitung (Quick Guide + Workflow +
vollständige Funktionsreferenz) wird **innerhalb der Desktop-App** über ein neues
**Hilfe-Menü** aufrufbar. Die Anleitung lebt als **eine kanonische Markdown-Datei**
(`ANLEITUNG_DESKTOP.md`), die sowohl im Repo als auch in der App dieselbe Quelle
ist — kein Drift, kein doppelter Text.

### Harte Anforderungen (vom Nutzer)

- **Keine halluzinierten Funktionen** — nur tatsächlich im Code vorhandene Bedienelemente.
- **Keine Funktion vergessen** — vollständige Abdeckung aller Controls/Aktionen.
- **Einheitliche Benennung** — exakt die UI-Labels aus `src/ui/strings.py`.
- **In-App aufrufbar** an geeigneter Stelle.

## Entscheidungen (aus Brainstorming)

1. **Zugriffspunkt:** Neue Menüleiste mit Menü **„Hilfe" → „Anleitung"**
   (App hat aktuell nur eine Toolbar, keine Menüleiste). Keine „Über"-Aktion in
   diesem Schritt (YAGNI; später trivial ergänzbar).
2. **Anzeige & Quelle:** In-App-Qt-Dialog, der eine gepflegte **Markdown-Datei**
   rendert (eine Quelle für Datei UND App).
3. **Doku-Struktur:** Die neue umfangreiche Anleitung **ersetzt** den Inhalt von
   `ANLEITUNG_DESKTOP.md` am bisherigen Ort (README-Link bleibt gültig).
   `BESCHREIBUNG.md` (Streamlit) und die OneNote-HTML bleiben unangetastet.

## Architektur & Komponenten

| Komponente | Datei | Aufgabe |
|---|---|---|
| Kanonische Anleitung | `ANLEITUNG_DESKTOP.md` (neu geschrieben, am Platz) | Single Source: Markdown-Anleitung |
| Ressourcen-Loader | `src/desktop/resources.py` (neu) | `manual_path() -> Path`, `load_manual_text() -> str`; dev vs. frozen |
| Anleitungs-Dialog | `src/desktop/manual_dialog.py` (neu) | `ManualDialog(QDialog)` mit `QTextBrowser.setMarkdown(...)`, scrollbar, Schließen-Button |
| Hilfe-Menü | `src/desktop/main_window.py` (kleine Ergänzung) | `QMenuBar` → „Hilfe" → Aktion „Anleitung" → öffnet `ManualDialog` |
| Texte | `src/ui/strings.py` | Neue Konstanten (siehe unten) |
| Packaging | `packaging/acc_viz.spec` | `ANLEITUNG_DESKTOP.md` zu `datas` ergänzen |

Begründung Modul-Trennung: Dialog-Logik liegt in `manual_dialog.py`, damit die
GUI-Entry-Datei `main_window.py` (~315 Zeilen) klein bleibt. Dort nur Menü-Aufbau
plus ein winziger `_show_manual`-Slot.

## Detail: Ressourcen-Loader (`src/desktop/resources.py`)

```python
import sys
from pathlib import Path

_MANUAL_FILENAME = "ANLEITUNG_DESKTOP.md"

def manual_path() -> Path:
    if getattr(sys, "frozen", False):
        base = Path(getattr(sys, "_MEIPASS"))   # PyInstaller bundle dir
    else:
        base = Path(__file__).resolve().parents[2]  # Projekt-Root
    return base / _MANUAL_FILENAME

def load_manual_text() -> str:
    return manual_path().read_text(encoding="utf-8")
```

- `parents[2]` von `src/desktop/resources.py` = Projekt-Root.
- Frozen: Spec legt die Datei nach `<bundle>/ANLEITUNG_DESKTOP.md` (Ziel `"."`),
  `sys._MEIPASS` zeigt auf den Bundle-Ordner.

## Detail: Anleitungs-Dialog (`src/desktop/manual_dialog.py`)

- `ManualDialog(QDialog)`:
  - Fenstertitel: `S.MANUAL_DIALOG_TITLE`.
  - `QTextBrowser` mit `setOpenExternalLinks(True)`, gefüllt via `setMarkdown(text)`.
  - Lädt Text über `load_manual_text()`; bei `OSError`/fehlender Datei →
    `setPlainText(S.MANUAL_LOAD_ERROR)` statt Crash.
  - Schließen-Button (`QDialogButtonBox.Close`).
  - Sinnvolle Startgröße (z. B. 760×620), resizable.
- Optionaler Konstruktor-Parameter `text: str | None = None` für Tests
  (umgeht Dateizugriff).

## Detail: Hilfe-Menü (`main_window.py`)

- Im `__init__`: `menubar = self.menuBar(); help_menu = menubar.addMenu(S.MENU_HELP)`.
- `manual_action = QAction(S.MENU_HELP_MANUAL, self)`,
  `triggered.connect(self._show_manual)`, `help_menu.addAction(manual_action)`.
- `self._manual_action` als Attribut (für Tests auffindbar).
- `_show_manual(self)`: erzeugt `ManualDialog(self)` und ruft `.exec()`
  (modal). Dialog als Attribut/lokal — kein Zustand nötig.

## Detail: Neue Strings (`src/ui/strings.py`)

```python
MENU_HELP = "Hilfe"
MENU_HELP_MANUAL = "Anleitung"
MANUAL_DIALOG_TITLE = "Anleitung — Beschleunigungs-Visualisierung"
MANUAL_LOAD_ERROR = "Anleitung konnte nicht geladen werden."
```

## Detail: Packaging (`packaging/acc_viz.spec`)

`added_files` ergänzen:

```python
added_files = [
    (str(project_root / "desktop_main.py"), "."),
    (str(project_root / "src"), "src"),
    (str(project_root / "ANLEITUNG_DESKTOP.md"), "."),   # NEU
]
```

## Inhalt der kanonischen Anleitung (`ANLEITUNG_DESKTOP.md`)

Strikt aus der Codebase abgeleitet. Verwendete Quell-Labels exakt aus
`strings.py` / `control_panel.py`. Gliederung:

1. **Kurzbeschreibung** — Band-RMS-Auswertung von Beschleunigungs-PSD an
   Plattenbohrungen; eine oder zwei Platten parallel.
2. **Quick Guide (5 Schritte)**
   1. Starten (`python3 desktop_main.py`)
   2. Ordner wählen — „Platte 1 — Ordnerpfad" (Pflicht) via 📁/Pfad;
      „Platte 2 — Ordnerpfad (optional)"; Auto-Analyse
   3. Einstellungen anpassen (Anzeige aktualisiert sofort)
   4. Spektrum ansehen — Klick auf weißen Kreis
   5. Exportieren — Toolbar „CSV exportieren"
3. **Workflow** — typischer Ablauf: Daten bereitstellen → Platte(n) laden →
   Frequenzband/Achse setzen → ggf. Normalisiert + Gemeinsame Farbskala für
   Vergleich → Interpolation/Methode → Heatmap/Histogramm lesen → Drilldown →
   Export.
4. **Eingabedaten** — Ordner pro Platte; `x{N}-y{M}.csv` (case-insensitiv,
   0-indiziert); Spalten `Frequenz_Hz, PSD_X_g2Hz, PSD_Y_g2Hz, PSD_Z_g2Hz`;
   optionale `Referenz.csv` (Voraussetzung für Normalisierung + Referenz-Stern).
5. **Funktionsreferenz** — jedes Bedienelement (vollständig, in Panel-Reihenfolge):
   - **Platte 1/2 — Ordnerpfad** (📁 „Ordner wählen" / Pfadeingabe)
   - **Frequenzband (Hz)** — 0–25 000, Schritt 100 Hz, min < max wird erzwungen
     (Mindestabstand 100 Hz); wirkt auf Heatmap, Spektrum-Hervorhebung, Export
   - **Achse** — X / Y / Z / RSS (= √(gRMS_X²+gRMS_Y²+gRMS_Z²))
   - **Normalisiert (relativ zur Referenz)** — teilt durch Referenz-RMS;
     Referenz = 1,0; erfordert `Referenz.csv`
   - **Interpolation** — an/aus; bei aus nur gemessene Zellen
   - **Interpolations-Methode** — „Linear (Delaunay)" / „Thin-Plate-Spline"
     (nur aktiv, wenn Interpolation an)
   - **Histogramm-Bins** — 5–50 (autom. auf Anzahl Löcher reduziert)
   - **Statistik anzeigen** — µ, Median, ±1σ im Histogramm
   - **Gemeinsame Farbskala** — gleicher zmin/zmax über beide Platten
   - **Farbskala** — Palette (Werte aus `COLORSCALES`; Viridis/Cividis empfohlen)
   - **CSV exportieren** (Toolbar) — pro Bohrung absoluter + normalisierter
     Band-RMS; UTF-8 mit BOM, Semikolon-getrennt
6. **Darstellung verstehen** — Heatmap (weiße Kreise = Bohrungen anklickbar,
   gelber Stern = Referenz in Plattenmitte; Achsen x-/y-Bohrung); Histogramm
   (Anzahl Löcher; optionale Statistik); Spektrum (PSD über Frequenz mit
   Referenzkurve und hervorgehobenem Band; bei RSS Summenkurve X+Y+Z).
7. **Referenz-Metrik** — pro Platte angezeigter Referenz-RMS bzw. „Normalisiert
   (Ref = 1.0)".
8. **Fehlermeldungen** — reale Meldungen aus `strings.py`: Pfad existiert nicht,
   kein Ordner, leerer Ordner, CSV-Lese-/Encoding-Fehler, fehlende Spalten,
   keine auswertbaren Messwerte; erscheinen in der Statusleiste/Inhaltsbereich.

## Tests (TDD)

Neue Tests unter `tests/desktop/`:

- `test_resources.py`:
  - `manual_path()` zeigt auf existierende Datei (dev).
  - `load_manual_text()` liefert nicht-leeren Text, enthält erwartete
    Abschnittsmarker (z. B. „Quick Guide", „Funktionsreferenz").
- `test_manual_dialog.py` (Qt, via vorhandener `conftest`-Fixtures):
  - `ManualDialog(text="...")` rendert nicht-leeren Inhalt.
  - Fehlerfall (nicht existierender Pfad gemockt) zeigt `MANUAL_LOAD_ERROR`.
- `test_main_window.py` / `test_main_window_integration.py` (Ergänzung):
  - Menü „Hilfe" und Aktion „Anleitung" existieren.
  - `_show_manual` erzeugt einen `ManualDialog` (exec gemockt, kein Blockieren).
- Konsistenz-Smoke: `ANLEITUNG_DESKTOP.md` enthält die erwarteten
  Abschnittsüberschriften (schützt vor versehentlichem Leeren der Datei).

## Nicht im Scope (YAGNI)

- „Über"-Dialog / Versionsanzeige (separat ergänzbar).
- Mehrsprachigkeit der Anleitung.
- Suchfunktion im Dialog / Inhaltsverzeichnis-Navigation.
- Änderungen an `BESCHREIBUNG.md` oder der OneNote-HTML.

## Versionierung

Neues, abwärtskompatibles Feature → **MINOR-Bump** auf `0.4.0` (README-Badge,
`pyproject.toml`/`VERSION`, Tag `v0.4.0`) gemäß Versionierungs-Workflow nach
Abschluss der Implementierung.
