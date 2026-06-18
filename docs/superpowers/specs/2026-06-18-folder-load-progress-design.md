# Schnelleres Laden + Fortschritts-Feedback beim Ordner-Laden

## Kontext

Beim Laden eines Messordners (typisch **50–70 Dateien × ~3,3 MB ≈ 200 MB**)
friert das Programm ein — unter Windows erscheint „Keine Rückmeldung". Ursache:

1. **UI-Thread-Blockade ohne Feedback.** `MainWindow._refresh` ruft
   `load_plates(settings.folders)` ([`main_window.py:129`](../../../src/desktop/main_window.py))
   **synchron auf dem UI-Thread** auf — ohne Cursor, ohne Fortschritt. Windows
   meldet jede App als „Keine Rückmeldung", deren Message-Loop ~5 s nicht
   zurückkehrt. (Der `analyze()`-Aufruf direkt darunter hat immerhin einen
   `WaitCursor`.)
2. **Langsamer Parser.** Jede CSV wird mit `pd.read_csv(..., engine="python")`
   ([`csv_reader.py:75`](../../../src/io/csv_reader.py)) geparst — die Python-Engine
   von pandas ist bei 3,3-MB-Dateien deutlich langsamer als die C-Engine, und die
   Dateien werden seriell in einer Schleife gelesen.

Zentrale technische Einsicht: **Ein Fortschrittsbalken allein entfernt „Keine
Rückmeldung" nicht** — solange die Arbeit auf dem UI-Thread läuft, bleibt das
Fenster eingefroren. Gewählter Ansatz (**Variante ① „Kooperativ"**): die
Ladeschleife bleibt auf dem UI-Thread, pumpt aber pro Datei die Events und
aktualisiert einen modalen Fortschrittsdialog. Da jede Datei mit der C-Engine nur
~Zehntelsekunden braucht, bleibt das Fenster flüssig und kommt nie an die
5-s-Schwelle. Kein Threading → der Aufruf bleibt aus Aufrufersicht **synchron**,
wodurch die bestehenden Desktop-Tests unverändert grün bleiben.

## Verhalten

- **Parser**: identisches Ergebnis, nur schneller (C-Engine).
- **Fortschritt**: Sobald ein Ladevorgang länger als ~400 ms dauert, erscheint ein
  modaler Dialog „Lade Messdateien…" mit Balken „Datei {i} von {n}" und
  Abbrechen-Button. Bei Cache-Treffern / kleinen Ordnern erscheint er gar nicht.
- **Abbruch**: Klick auf Abbrechen stoppt das Laden; der **vorherige Zustand
  bleibt erhalten** (View wird nicht geleert), kurze Statusbar-Notiz „Laden
  abgebrochen".
- **Erwartetes Ergebnis**: ~200 MB von *~30–60 s eingefroren* → *~5–10 s mit
  laufendem Balken*, keine „Keine Rückmeldung" mehr.

## Architektur / Datenfluss

```
ControlPanel.set_folder → settingsChanged → MainWindow._refresh
  └─ folders_changed:
       QProgressDialog erstellen (modal, minimumDuration≈400ms)
       load_plates(folders, progress=cb)            ← cb läuft auf UI-Thread
         └─ _cached_load(folder, progress=…)         ← Cache-Treffer: kein cb
              └─ load_plate(folder, progress=…)
                   pro Datei: read_measurement_csv() ; cb(i, total, name)
       cb(i, total, name): dialog.setValue(i); dialog.setLabelText(...)
                           QApplication.processEvents()
                           if dialog.wasCanceled(): raise LoadCancelled
       except LoadCancelled: vorherigen Zustand behalten, Statusnotiz
       finally: dialog.close()
  └─ danach unverändert: analyze() (WaitCursor) → _render()
```

`core/pipeline.py` bleibt **Qt-frei** — der Fortschritt fließt nur über einen
einfachen `Callable`. Die Qt-Spezifika (Dialog, `processEvents`, `wasCanceled`)
liegen ausschließlich in `desktop/main_window.py`.

## Änderungen

### `src/io/schema.py`
Neu (am Ende, neben den bestehenden Exceptions):
```python
from collections.abc import Callable

# (erledigte_dateien, gesamt_dateien, aktueller_dateiname)
ProgressCallback = Callable[[int, int, str], None]

class LoadCancelled(Exception):
    """Vom Fortschritts-Callback ausgelöst, um einen Ladevorgang abzubrechen.

    Bewusst **kein** AccVizError: load_plates wandelt AccVizError pro Platte in
    Fehlerstrings um — ein Abbruch darf dort nicht hängenbleiben, sondern muss
    durchpropagieren.
    """
```

### `src/io/csv_reader.py`
- In `read_measurement_csv`: `engine="python"` → `engine="c"`. Sonst nichts.
- `usecols` wird **nicht** eingeführt (optionaler Folge-Schritt; würde den
  Schema-Fehler-Pfad berühren).

### `src/io/plate_loader.py`
- `load_plate(folder, *, progress: ProgressCallback | None = None)`.
- Vor der Leseschleife die passenden Einträge sammeln (Hole-Dateien **und**
  optionale `Referenz.csv`), um `total` zu kennen. Reihenfolge wie bisher
  (`sorted(folder_path.iterdir())`).
- Beim Lesen jeder zu parsenden Datei **vor** dem `read_measurement_csv`-Aufruf
  `progress(i, total, name)` aufrufen (1-basierter Index oder 0-basiert — im Plan
  fixieren; Tests prüfen Monotonie und Endwert == total).
- `progress` ist optional; ohne Callback verhält sich `load_plate` exakt wie
  bisher. Ein `LoadCancelled` aus dem Callback propagiert ungehindert.

### `src/core/pipeline.py`
- `_folder_mtime_token` unverändert.
- `_cached_load(folder, *, progress=None)`: bei **Cache-Treffer** wird `progress`
  **nicht** aufgerufen (sofort); bei Miss an `load_plate` durchreichen.
- `load_plates(folders, *, progress=None)`: Callback durchreichen und zu **einem
  monotonen** Balken `0..Gesamtsumme` über alle Ordner aggregieren (laufender
  Offset je Ordner). Mechanik im Plan festlegen; beobachtbarer Vertrag: monoton
  steigend, Endwert == Summe der geladenen Dateien.
- **Wichtig**: in der Schleife ein `except LoadCancelled: raise` **vor** dem
  bestehenden `except AccVizError` / `except Exception`, damit ein Abbruch nicht
  in einen Platten-Fehlerstring umgewandelt wird.

### `src/desktop/main_window.py`
- In `_refresh`, Zweig `folders_changed`:
  - `QProgressDialog` erzeugen (`parent=self`, `Qt.WindowModal`/application-modal,
    `setMinimumDuration(400)`, `setAutoClose(False)`, `setAutoReset(False)`).
  - Callback definieren: `setLabelText`, `setRange(0, total)` (einmalig beim
    ersten Call, sobald `total` bekannt), `setValue(i)`, `QApplication.processEvents()`,
    `if dlg.wasCanceled(): raise LoadCancelled`.
  - `load_plates(settings.folders, progress=cb)` in `try/except LoadCancelled`;
    `finally: dlg.close()`.
  - **Abbruch-Semantik**: `self._load`/`self._settings` auf dem vorherigen Stand
    belassen (nicht `_reset_state`), `self._settings` so zurücksetzen, dass ein
    erneuter identischer `settingsChanged` wieder einen Ladeversuch auslöst;
    Statusbar `S.LOAD_CANCELLED`, Methode früh verlassen.
- Der `WaitCursor` um `analyze()` bleibt **unverändert**.
- GUI-Entry-File-Regel beachten: `main_window.py` liegt bei 325 Zeilen. Falls die
  Dialog-/Callback-Logik die Datei über ~400 Zeilen treibt, in einen kleinen
  Helfer (`desktop/load_progress.py`) auslagern statt anhängen.

### `src/core/strings.py`
Neue Konstanten (deutsche UI-Texte):
- `LOAD_PROGRESS_TITLE = "Lade Messdateien…"`
- `LOAD_PROGRESS_LABEL = "Datei {i} von {n}"`  (oder mit Dateiname)
- `LOAD_CANCEL = "Abbrechen"`
- `LOAD_CANCELLED = "Laden abgebrochen"`

## Tests (TDD)

### `tests/io/test_plate_loader.py`
- `progress` wird genau **einmal pro zu parsender Datei** aufgerufen, mit
  korrektem `total` und monoton steigendem Index; Endwert == Dateianzahl.
- `LoadCancelled`, ausgelöst im Callback, **bricht ab** und propagiert (keine
  weiteren Dateien gelesen — über einen Callback prüfbar, der beim 2. Aufruf
  wirft, und Zählung der `read`-Aufrufe).
- Ohne `progress` unverändertes Verhalten (Bestandstests bleiben grün).

### `tests/io/test_csv_reader.py`
- Komplette Bestands-Suite bleibt mit `engine="c"` grün (Regressionswächter für
  Separator/`decimal=","`/BOM/`skiprows`/Header-Suche).

### `tests/core/test_pipeline.py`
- `load_plates(..., progress=cb)` propagiert `LoadCancelled` (wird **nicht** zu
  einem Fehlerstring in `PlateLoad.errors`).
- Fortschritt aggregiert monoton über **zwei** Ordner.
- Cache-Treffer ruft `progress` nicht auf.

### `tests/desktop/test_main_window.py`
- Bestandstests bleiben grün (synchroner `_refresh`).
- Neuer Test: bei einem Mehrdatei-Ordner wird der Dialog getrieben — über
  `monkeypatch` auf einen Fake-`QProgressDialog`, der `setValue`-Aufrufe sammelt.
- Neuer Test: `wasCanceled()==True` bricht ab; vorheriges `_analysis` bleibt
  erhalten; kein hängender Override-Cursor (analog `test_refresh_resets_override_cursor`).

## Verifikation

1. `python3 desktop_main.py`
2. Großen Messordner (50–70 Dateien) laden → modaler Dialog erscheint nach kurzer
   Zeit, Balken läuft „Datei i von 70", Fenster bleibt reagierbar (kein „Keine
   Rückmeldung").
3. Während des Ladens **Abbrechen** klicken → Laden stoppt, vorherige Ansicht
   bleibt, Statusnotiz „Laden abgebrochen".
4. Kleinen Ordner / bereits geladenen (Cache) laden → kein Dialog-Flackern.
5. `pytest` → alle Tests grün.

## Nicht-Ziele (YAGNI)

- Kein Hintergrund-Thread / keine parallelen Reads (= Variante ②, später).
- `analyze()` bleibt auf dem UI-Thread (≤2 Platten, <1 s).
- Kein `usecols` (optionaler Folge-Schritt).
- Keine Änderung an Cache-Größe, Interpolation oder Render-Pfad.
