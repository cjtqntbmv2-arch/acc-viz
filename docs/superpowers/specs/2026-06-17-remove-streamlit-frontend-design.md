# Spec: Streamlit-Frontend vollständig entfernen (Desktop-only)

**Datum:** 2026-06-17
**Status:** Approved (Design)
**Version-Ziel:** 0.5.0

## Ziel & Motivation

Das Projekt enthält aktuell zwei Frontends, die sich denselben Kern teilen:

- **Streamlit** (Legacy): `app.py` + `src/ui/`
- **Desktop** (PySide6/Qt): `desktop_main.py` + `src/desktop/`

Das Streamlit-Frontend war als Übergangslösung gedacht und ist seit dem Desktop-Port redundant. Es soll **vollständig entfernt** werden. Übrig bleibt eine reine PySide6-Desktop-App.

**Harte Anforderung:** Es dürfen **keinerlei Rückstände oder Hinweise** auf das Streamlit-Frontend mehr im aktiven Repo verbleiben — weder Code, Config, Dependencies, Doku, Docstrings noch Kommentare. (Ausnahme: die historischen, datierten Dateien unter `docs/superpowers/specs/` und `docs/superpowers/plans/` bleiben als Projekt-Historie unangetastet — sie dokumentieren vergangene Entscheidungen.)

## Ausgangslage (Kopplungsanalyse)

`src/ui/` enthält **zwei Sorten** Code:

- **Reines Streamlit:** `sidebar.py`, `heatmap.py`, `histogram.py`, `spectrum.py`, `export.py`
- **Geteilter Code** (von `src/core/pipeline.py` und der Desktop-App genutzt): `strings.py`, `errors.py`

`src/ui/errors.py` importiert intern `from src.ui import strings`. `src/ui/strings.py` ist frontend-agnostischer UI-Text (deutsche Labels/Meldungen).

## Designentscheidungen

1. **Geteilter Code wandert nach `src/core/`** (nicht nach `src/desktop/`, da `src/core/pipeline.py` ihn importiert — `core` darf nicht von `desktop` abhängen). Das Paket `src/ui/` verschwindet danach vollständig.
2. **Tests für geteilten Code werden mitgenommen**, nicht gelöscht (kein Coverage-Verlust).
3. **Historische Design-Docs bleiben unberührt** (dokumentierte Historie, kein Rewrite der Vergangenheit).
4. **Versionssprung MINOR → 0.5.0** (pre-1.0; Entfernen eines Frontends ist strukturell groß, aber unter 1.0 als MINOR geführt).

## Umfang der Änderungen

### A. Dateien löschen (reines Streamlit)

- `app.py`
- `src/ui/sidebar.py`, `src/ui/heatmap.py`, `src/ui/histogram.py`, `src/ui/spectrum.py`, `src/ui/export.py`
- `tests/ui/test_sidebar.py`, `test_heatmap.py`, `test_histogram.py`, `test_smoke.py` (Streamlit-Smoke), `test_export.py`
  - `test_export.py` testet nur den Streamlit-Re-Export von `build_export_dataframe`; die echte Logik liegt in `src/core/export.py` und ist über `tests/core/` + `tests/desktop/test_export.py` abgedeckt.

### B. Geteilten Code + zugehörige Tests verschieben

- `src/ui/strings.py` → `src/core/strings.py`
- `src/ui/errors.py` → `src/core/errors.py` (interner Import `src.ui.strings` → `src.core.strings`)
- `tests/ui/test_strings.py` → `tests/core/test_strings.py` (Import angepasst)
- `tests/ui/test_errors.py` → `tests/core/test_errors.py` (Import angepasst)
- Danach `tests/ui/` vollständig löschen (inkl. `__init__.py`, `conftest.py`)
- `src/ui/__init__.py` löschen → Paket `src/ui/` existiert nicht mehr

### C. Importe aktualisieren

Alle `from src.ui import strings as S` → `from src.core import strings as S`
Alle `from src.ui.errors import format_error` → `from src.core.errors import format_error`

Betroffene aktive Dateien (mind.):
`src/core/pipeline.py`, `src/desktop/main_window.py`, `src/desktop/control_panel.py`, `src/desktop/export.py`, `src/desktop/manual_dialog.py`, `src/desktop/plots/spectrum_canvas.py`, `src/desktop/plots/heatmap_canvas.py`, `src/desktop/plots/histogram_canvas.py`, sowie `src/core/errors.py` (interner Import).

### D. Dependencies bereinigen

- `requirements.txt`: `streamlit>=1.35.0` + `plotly>=5.18.0` samt Legacy-Kommentarblock entfernen
- `pyproject.toml`: Optional-Extra `web = ["streamlit...", "plotly..."]` streichen
- `packaging/acc_viz.spec`: `"streamlit"`-Eintrag aus der `excludes`-Liste entfernen (nicht mehr nötig)

### E. Doku & Kommentare scrubben (kein Streamlit/Plotly/app.py-Hinweis mehr)

- `README.md`: Abschnitt „Streamlit-App (Legacy-Frontend)" + `streamlit run app.py`-Zeile entfernen
- `BESCHREIBUNG.md`: **Überarbeitung** — beschreibt aktuell eine „Streamlit-App" mit „Plotly-Heatmaps" (interaktiv, Plotly-Farbpalette). Auf die Desktop-App (PySide6 + matplotlib) umschreiben; Plotly/Streamlit-Begriffe entfernen; Start-Befehl `streamlit run app.py` → `python3 desktop_main.py`.
- Docstrings/Kommentare in aktiven Dateien bereinigen (verwaiste Verweise „Mirrors `src.ui.X`…", „Extracted from Streamlit `app.py`…", „original Streamlit"):
  `desktop_main.py`, `src/core/pipeline.py`, `src/core/export.py`, `src/core/colorscales.py`, `src/core/settings.py`, `src/desktop/control_panel.py`, `src/desktop/main_window.py`, `src/desktop/manual_dialog.py`, `src/desktop/export.py`, `src/desktop/plots/{spectrum,heatmap,histogram}_canvas.py`, `src/platform_utils/folder_picker.py`
  → jeweils auf aktuellen Stand bringen (Verweis auf nicht-mehr-existenten Streamlit-Code entfernen, ggf. durch Beschreibung der eigentlichen Funktion ersetzen).
- `ANLEITUNG_DESKTOP.md` und `ANLEITUNG_DESKTOP_onenote.html`: bereits Streamlit-frei (verifiziert) — nur Gegencheck.

## Verifikation (Definition of Done)

1. **Repo-weiter Gegencheck** (außerhalb `docs/superpowers/` und `.git/`): keine Treffer mehr für `streamlit`, `plotly`, `src.ui`, `src/ui`, `app.py`.
   ```
   grep -rIn -e streamlit -e plotly -e 'src\.ui' -e 'src/ui' -e 'app\.py' . \
     --exclude-dir=.git --exclude-dir=docs/superpowers --exclude-dir=node_modules
   ```
   (Nur historische `docs/superpowers/`-Treffer sind erlaubt.)
2. **Volle Testsuite grün** (`python3 -m pytest`) — reduzierte Zahl gegenüber 201 (Streamlit-Tests entfernt), keine Failures/Errors.
3. **`pyright` sauber** (CI-blocking, 0 Fehler).
4. **Desktop-App startet** (`python3 desktop_main.py`).
5. `src/ui/`-Verzeichnis existiert nicht mehr.

## Versionierung

- Bump auf **0.5.0** in `pyproject.toml` (Source of Truth) + README-Badge synchron.
- Annotated Tag `v0.5.0` auf dem Bump-Commit, push mit `--follow-tags`.
- Vorher Konsistenzcheck: pyproject == README-Badge, kein `v0.5.0`-Tag vorhanden.

## Nicht im Umfang (YAGNI)

- Keine Umbenennung/Reorganisation des `src/desktop/`-Pakets.
- Keine funktionalen Änderungen an der Desktop-App.
- Kein Anfassen der historischen `docs/superpowers/`-Dateien.
