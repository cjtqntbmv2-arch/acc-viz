# Schnelleres Laden + Fortschritts-Feedback beim Ordner-Laden

## Kontext

Beim Laden eines Messordners (typisch **50–70 Dateien × ~3,3 MB ≈ 200 MB**)
friert das Programm ein — unter Windows erscheint „Keine Rückmeldung". Ursache:

1. **UI-Thread-Blockade ohne Feedback.** `MainWindow._refresh` ruft
   `load_plates(settings.folders)` ([`main_window.py:129`](../../../src/desktop/main_window.py))
   **synchron auf dem UI-Thread** auf — ohne Cursor, ohne Fortschritt. Windows
   meldet jede App als „Keine Rückmeldung", deren Message-Loop ~5 s nicht
   zurückkehrt.
2. **Langsamer Parser.** Jede CSV wird mit `pd.read_csv(..., engine="python")`
   ([`csv_reader.py:75`](../../../src/io/csv_reader.py)) geparst — die Python-Engine
   ist bei 3,3-MB-Dateien deutlich langsamer als die C-Engine.

Gewählter Ansatz (**Variante ① „Kooperativ"**): die Ladeschleife bleibt auf dem
UI-Thread, pumpt aber pro Datei die Events und aktualisiert einen modalen
`QProgressDialog`. Mit der C-Engine parst jede Datei in ~Zehntelsekunden, das
Fenster bleibt flüssig und kommt nie an die 5-s-Schwelle. Kein Threading → der
Aufruf bleibt aus Aufrufersicht **synchron**, wodurch bestehende Desktop-Tests
unverändert grün bleiben.

> **Empirisch bestätigt** (Grill-Runde, Worktree): `engine="c"` ist
> verhaltensgleich (alle CSV-Tests grün), ein echter `QProgressDialog` ist unter
> `offscreen` ohne Event-Loop voll steuerbar, und **queued Signals feuern während
> `processEvents()`** — deshalb braucht es einen Re-Entrancy-Guard (siehe unten).

## Verhalten

- **Parser**: identisches Ergebnis, nur schneller (C-Engine).
- **Fortschritt**: Sobald ein Ladevorgang länger als ~400 ms dauert, erscheint ein
  **application-modaler** Dialog „Lade Messdateien…" mit Balken „Datei {i} von {n}"
  und Abbrechen-Button. Der Dialog wird **erst beim ersten echten Fortschritt
  lazy konstruiert** → bei Cache-Treffern / kleinen Ordnern entsteht gar kein
  Widget, kein Flackern.
- **Abbruch (komplett rückgängig)**: Klick auf Abbrechen stoppt das Laden und
  setzt **Ordnerfeld _und_ Ansicht auf den letzten erfolgreichen Stand zurück**
  (roher Feldtext-Snapshot wird vor dem Laden gehalten; Wiederherstellen erfolgt
  mit `blockSignals`, damit kein sofortiger Reload ausgelöst wird). `self._settings`
  wird auf `prev` zurückgesetzt, kurze Statusbar-Notiz „Laden abgebrochen". Feld
  und Ansicht bleiben so konsistent; wer den Ordner doch will, wählt ihn erneut.
- **Re-Entrancy**: ein `self._is_loading`-Flag schützt `_refresh` davor, während
  des `processEvents()` durch ein queued `settingsChanged` rekursiv erneut
  einzutreten.
- **Erwartetes Ergebnis**: ~200 MB von *~30–60 s eingefroren* → *~5–10 s mit
  laufendem Balken*, keine „Keine Rückmeldung" mehr.

## Architektur / Datenfluss

```
ControlPanel.set_folder → settingsChanged → MainWindow._refresh
  └─ if self._is_loading: return                 # Re-Entrancy-Guard
  └─ folders_changed:
       snapshot = control_panel.folder_texts()    # roher Feldtext-Stand vorher? (siehe Cancel)
       self._is_loading = True
       try:  loaded = load_with_progress(self, folders)
       finally: self._is_loading = False
       if loaded is None:                          # abgebrochen
            control_panel.restore_folder_texts(self._last_good_folder_texts)
            self._settings = prev
            statusBar: LOAD_CANCELLED ; return
       self._last_good_folder_texts = control_panel.folder_texts()
       load = loaded ; ... (Fehler in Statusbar) ...
  └─ danach unverändert: analyze() (WaitCursor) → _render()

load_with_progress(parent, folders, *, dialog_factory=None):
  dlg = None
  on_progress(done, total, name):
      if dlg is None: dlg = factory(); konfigurieren; setRange(0,total)  # lazy
      dlg.setValue(done); dlg.setLabelText("Datei done von total")
      QApplication.processEvents()
      if dlg.wasCanceled(): raise LoadCancelled
  try: return load_plates(folders, progress=on_progress)
  except LoadCancelled: return None
  finally: if dlg is not None: dlg.close()
```

`core/pipeline.py` und `io/*` bleiben **Qt-frei** — Fortschritt fließt nur über
einen einfachen `Callable`; alle Qt-Spezifika liegen in `desktop/load_progress.py`.

## Änderungen

### `src/io/schema.py`
Neu: Typalias `ProgressCallback = Callable[[int, int, str], None]` (erledigt,
gesamt, dateiname) und `class LoadCancelled(Exception)` — bewusst **kein**
`AccVizError` (sonst würde `load_plates` den Abbruch in einen Platten-Fehlerstring
umwandeln).

### `src/io/csv_reader.py`
`engine="python"` → `engine="c"`. Sonst nichts. (`usecols` bleibt draußen.)

### `src/io/plate_loader.py`
- `_is_plate_file(entry)` als gemeinsames Prädikat (Hole-Pattern **oder**
  Referenz) — von Loader **und** `count_plate_files` genutzt (eine Wahrheit).
- `count_plate_files(folder) -> int`: Zahl der Dateien, die `load_plate` parsen
  würde; `0` bei ungültigem Ordner.
- `load_plate(folder, *, progress=None)`: sammelt zuerst `to_parse` (für `total`),
  ruft dann `progress(i, total, name)` **1-basiert, vor** dem Lesen jeder Datei.

### `src/core/pipeline.py`
- `load_plates(folders, *, progress=None)` mit **einem** monotonen Balken
  `0..Gesamtsumme`:
  - `counts = [count_plate_files(f) for _, f in folders]` (einmal vorab, alle
    Ordner), `grand_total = sum(counts)`.
  - Pro Ordner `inner = _make_inner(progress, base, grand_total)` (eine
    benannte Factory mit sauberer 3-Arg-Closure — **pyright-konform**, kein
    `inner: … = None` + `def inner`).
  - `base += counts[idx]` **auf allen Pfaden** (Erfolg/Fehler) via `finally`, damit
    der Balken bei einer korrupten CSV mitten im Ordner nicht rückwärts läuft und
    immer `grand_total` erreicht.
  - `_cached_load(folder, *, progress=…)` reicht den Callback bei Miss durch; bei
    Cache-Treffer wird `load_plate`/`progress` gar nicht erst aufgerufen.
  - `except LoadCancelled: raise` **vor** `except AccVizError` / `except Exception`.
  - **`_is_cached` entfällt** (die globale Summe rechnet sauber, auch wenn ein
    Ordner doppelt gewählt wird).

### `src/io` / `core` Tests
Autouse-Fixture, die das modulweite `_LOAD_CACHE` vor jedem Test leert (macht den
Cache-Treffer-Test deterministisch).

### `src/core/strings.py`
`LOAD_PROGRESS_TITLE = "Lade Messdateien…"`, `LOAD_PROGRESS_LABEL = "Datei {i} von {n}"`,
`LOAD_CANCEL = "Abbrechen"`, `LOAD_CANCELLED = "Laden abgebrochen"`.

### `src/desktop/load_progress.py` (neu)
`load_with_progress(parent, folders, *, dialog_factory=None) -> PlateLoad | None`.
Dialog **lazy** bei erstem Fortschritt (Titel + Abbrechen-Text über den
Konstruktor), `ApplicationModal`, `setMinimumDuration(400)`,
`setAutoClose(False)`, `setAutoReset(False)`. Gibt `None` bei Abbruch zurück.
`dialog_factory`-Seam für Tests (Fake-Dialog, kein echtes Widget nötig).

### `src/desktop/control_panel.py`
- `folder_texts() -> list[str]`: rohe Feldtexte.
- `restore_folder_texts(texts)`: Felder setzen **mit `blockSignals`** (kein
  Re-Trigger).

### `src/desktop/main_window.py`
- `__init__`: `self._is_loading = False`, `self._last_good_folder_texts =
  control_panel.folder_texts()`.
- `_refresh`: Guard `if self._is_loading: return`; Lade-Zweig ruft
  `load_with_progress(self, settings.folders)` (Top-Level-Import, damit
  monkeypatchbar) in `try/finally` um das Guard-Flag; bei `None` → Option-A-Abbruch
  (Felder + Ansicht zurück, `self._settings = prev`, Statusnotiz, return); bei
  Erfolg `_last_good_folder_texts` aktualisieren.
- `WaitCursor` um `analyze()` bleibt **unverändert**.

## Tests (TDD)

- **schema**: `LoadCancelled` ist kein `AccVizError`; `ProgressCallback` exportiert.
- **csv_reader**: Bestands-Suite (11 Tests) bleibt mit `engine="c"` grün + ein
  Viele-Zeilen-Test (Semikolon/Dezimalkomma).
- **plate_loader**: `progress` genau einmal je Datei (1-basiert, monoton,
  Endwert==Anzahl); ohne `progress` unverändert; `LoadCancelled` bricht früh ab;
  `count_plate_files` == Zahl der `progress`-Aufrufe (auch mit Stör-`.csv`).
- **pipeline**: `LoadCancelled` propagiert (kein Fehlerstring); **ein** globaler
  Balken `[1,2,3,4]` über zwei Ordner; Cache-Treffer ⇒ keine `progress`-Aufrufe;
  korrupte CSV in Ordner 1 von 2 ⇒ Balken monoton, erreicht `grand_total`.
- **control_panel**: `folder_texts`/`restore_folder_texts` round-trip; Restore löst
  **kein** `settingsChanged` aus.
- **load_progress**: Fake-Dialog wird getrieben (`values==[1,2]`, lazy
  konstruiert); Abbruch ⇒ `None`, Dialog geschlossen.
- **main_window**: Bestand grün; Abbruch ⇒ Feld **und** `_analysis`/`_load`
  unverändert auf altem Stand, Statusbar zeigt `LOAD_CANCELLED`; kein hängender
  Override-Cursor.

## Verifikation

1. `pytest` (≈ 166 + 13 neue = ~179) und `pyright` (CI-Gate) grün.
2. `python3 desktop_main.py`, 50–70-Datei-Ordner laden → Dialog nach kurzer Zeit,
   Balken „Datei i von 70", Fenster reagierbar, kein „Keine Rückmeldung".
3. Während des Ladens **Abbrechen** → Laden stoppt, Feld **und** Ansicht zurück auf
   vorher, Statusnotiz „Laden abgebrochen".
4. Kleinen/gecachten Ordner laden → kein Dialog-Flackern.

## Nicht-Ziele (YAGNI)

- Kein Hintergrund-Thread / keine parallelen Reads (= Variante ②, später).
- `analyze()` bleibt auf dem UI-Thread (≤2 Platten, <1 s).
- Kein `usecols`; keine Änderung an Cache-Größe, Interpolation oder Render-Pfad.
