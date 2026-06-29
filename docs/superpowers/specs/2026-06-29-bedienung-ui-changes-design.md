# Bedienungs-Änderungen: Frequenzband-Commit, Histogramm-Toggle, RSS-Spektrum, Mehrfach-Messpunkte

**Datum:** 2026-06-29
**Status:** Genehmigt (Design)

## Ziel

Sechs Verbesserungen an der Bedienung der Desktop-App. Vier vom Nutzer
angefragt, zwei kleine Ergänzungen, die direkt zu Anfrage #4 bzw. #2 gehören.

## Scope

| # | Änderung | Kernfile(s) |
|---|----------|-------------|
| 1 | Frequenzband rechnet erst bei Enter / Fokuswechsel, nicht pro Tastenanschlag | `control_panel.py` |
| 2 | Checkbox „Histogramm anzeigen" | `control_panel.py`, `settings.py`, `main_window.py` |
| 3 | RSS-Spektrum zeigt nur die Summenkurve (keine X/Y/Z-Einzellinien) | `spectrum_canvas.py` |
| 4 | Mehrere Messpunkte überlagert in einem Spektrum | `main_window.py`, `spectrum_canvas.py` |
| 5 | Gewählte Löcher auf der Heatmap markieren (gehört zu #4) | `heatmap_canvas.py`, `main_window.py` |
| 6 | „Bins"/„Statistik" ausgrauen, wenn Histogramm aus ist (gehört zu #2) | `control_panel.py` |

Nicht im Scope (bewusst weggelassen, YAGNI): Referenzlinie als eigene Checkbox,
„Auswahl leeren"-Button, Export der Mehrfachauswahl.

---

## 1. Frequenzband: Commit statt Live-Recompute

**Problem:** Die beiden `QSpinBox`-Felder (`_f_min`, `_f_max`) feuern
`valueChanged` bei jedem Tastenanschlag → die teure Pipeline läuft schon ab der
ersten getippten Ziffer.

**Lösung:** `setKeyboardTracking(False)` auf beiden Spinboxen. Damit emittiert
`valueChanged` nur noch bei **Enter**, **Fokusverlust** oder Klick auf die
Step-Pfeile — nicht beim Tippen. Native Qt-Funktion, keine Timer, kein Button.

Die bestehende Clamp-Logik (`_on_f_min_changed` / `_on_f_max_changed`,
`f_max > f_min` mit `_FREQ_STEP`-Abstand) bleibt unverändert und läuft genau
einmal pro Commit.

**Edge Case:** Step-Pfeile committen weiterhin sofort pro Klick — gewollt, das
ist ein bewusster Einzelschritt.

---

## 2. Checkbox „Histogramm anzeigen"

**Settings:** Neues Feld `Settings.show_histogram: bool = True` (reines
Anzeige-Feld, **nicht** in `_COMPUTE_FIELDS` von `main_window.py`).

**Control-Panel:** Neue `QCheckBox` (Default checked), `toggled` →
`settingsChanged`. Neuer String `S.SHOW_HISTOGRAM` + Hilfetext. In
`current_settings()` mit aufnehmen.

**Rendering:** In `_build_plate_column` wird der `HistogramCanvas`-Block nur
gebaut/hinzugefügt, wenn `settings.show_histogram` wahr ist.

**Verhalten:** Umschalten ändert die Settings → `_refresh` erkennt
„Settings ≠ prev", Ordner unverändert (kein Reload), Compute-Felder unverändert
(kein Re-Analyze) → nur `_render`. Kein teures Neuladen.

---

## 3. RSS-Spektrum: nur die Summenkurve

**Änderung:** In `SpectrumCanvas._add_rss_traces` entfällt die `for a in
_SINGLE_AXES`-Schleife, die X/Y/Z einzeln plottet. Es bleibt die schwarze
RSS-Summenkurve (`_rss_sum`) plus optionale Referenz.

Strings `SPECTRUM_TRACE_AXIS_TMPL` werden danach evtl. nicht mehr gebraucht —
prüfen und ggf. entfernen (nur wenn nirgends sonst referenziert).

---

## 4. Mehrere Messpunkte überlagert

### Auswahl-Logik (in `MainWindow`)

- Zustand: `self._selected_points: list[tuple[str, int, int]]` (geordnet,
  `(plate_name, x, y)`).
- `_on_hole_clicked(name, x, y)`: liest
  `QApplication.keyboardModifiers()`.
  - **Strg/Cmd gehalten** (`Qt.KeyboardModifier.ControlModifier` — Qt mappt Cmd
    auf macOS automatisch auf ControlModifier): Punkt togglen (hinzufügen, wenn
    nicht vorhanden; entfernen, wenn schon drin).
  - **Ohne Modifier:** Auswahl auf genau diesen einen Punkt zurücksetzen
    (bisheriges Verhalten).
- Kein Eingriff in das `holeClicked`-Signal der Heatmap — Modifier wird im
  bestehenden Slot gelesen.

### Farb-Zuordnung

Farbe eines Punktes = `f"C{i % 10}"` über seinen Index `i` in
`_selected_points` (matplotlib-Default-Zyklus). Dieselbe Farbe wird für die
Spektrum-Linie **und** den Heatmap-Marker (#5) verwendet → visuelle Kopplung.

### Darstellung (`SpectrumCanvas`)

`render_spectrum` wird auf eine **geordnete Punktliste** umgestellt. Jeder
Eintrag trägt: `plate_name, x, y, color, hole_df, ref_df`.

- **Einzelachse (X/Y/Z):** pro Punkt eine Linie in seiner Farbe, Label
  `„{plate} – ({x}, {y})"`.
- **RSS:** pro Punkt eine RSS-Summenkurve in seiner Farbe (kombiniert mit #3).
- **Referenzlinie:** nur bei **genau einem** gewählten Punkt (heutiges
  Verhalten); bei mehreren weggelassen.
- **Titel:** bei einem Punkt der bisherige Detail-Titel; bei mehreren ein
  generischer Titel (z. B. „Spektrum – {axis}, {n} Punkte").
- Legende kennzeichnet Platte + Loch je Linie.

Neuer String `S.SPECTRUM_TRACE_POINT_TMPL = "{plate} – ({x}, {y})"`.

### Persistenz über Re-Renders

`_render` zeichnet nach dem Aufbau der Plattenspalten + Spektrum-Container das
kombinierte Spektrum neu, **wenn `_selected_points` nicht leer ist** — mit der
aktuellen Achse / dem aktuellen Band. So überlebt die Auswahl einen
Band-Commit (#1) oder Achswechsel.

- Hole-DFs werden aus dem aktuellen `self._load` neu geholt (bei reinem
  Band-/Achswechsel unverändert, da Ordner gleich).
- **Bei Ordnerwechsel** (`folders_changed`) wird `_selected_points` geleert —
  andere Platten, alte Punkte ungültig.
- Punkte, deren `(plate, x, y)` im neuen Load fehlen, werden beim Neuzeichnen
  übersprungen (defensiv).

---

## 5. Gewählte Löcher auf der Heatmap markieren

`HeatmapCanvas.render_grid` erhält einen neuen Parameter
`selected: list[tuple[int, int, str]]` (x, y, color) — die für **diese** Platte
gewählten Punkte mit ihrer Spektrum-Farbe.

Gezeichnet als zusätzlicher `scatter`: hohler Ring (`facecolors="none"`),
`edgecolors=color`, größer als die normalen Loch-Marker, hoher `zorder` (über
den normalen Markern). So sieht man auf einen Blick, welche Löcher gerade im
Spektrum liegen — auch plattenübergreifend.

`_build_plate_column` filtert `_selected_points` auf die aktuelle Platte und
reicht `(x, y, color)` je Punkt (Farbe über globalen Index) durch.

Default `selected=[]` (oder `None`) → keine Verhaltensänderung, wenn nichts
gewählt ist.

---

## 6. „Bins"/„Statistik" ausgrauen bei verstecktem Histogramm

Analog zum bestehenden Muster Interpolation→Methode
(`_on_interpolate_toggled` → `setEnabled`):

Ein Slot `_on_show_histogram_toggled(checked)` setzt `_bins.setEnabled(checked)`
und `_histogram_stats.setEnabled(checked)` und emittiert `settingsChanged`. Die
Felder bleiben in den Settings gültig, sind nur ausgegraut, wenn das Histogramm
aus ist.

---

## Testing

TDD pro Einheit, jeweils failing-test zuerst:

1. **Frequenzband:** `control_panel`-Test — `_f_min`/`_f_max` haben
   `keyboardTracking == False`. (Reine Property-Prüfung, da Tipp-Events im
   Headless-Test schwer zu simulieren sind.)
2. **show_histogram:** `settings`-Default-Test; `control_panel.current_settings`
   spiegelt die Checkbox; `main_window`-Render-Test — bei `show_histogram=False`
   wird kein `HistogramCanvas` in der Spalte gebaut.
3. **RSS-Spektrum:** `spectrum_canvas`-Test — im RSS-Modus genau eine
   Summenlinie (+ ggf. Ref), keine drei Achsenlinien (Linienanzahl prüfen).
4. **Mehrfachauswahl:** `main_window`-Test — Strg+Klick akkumuliert
   `_selected_points`; Klick ohne Modifier setzt zurück; Spektrum überlebt einen
   Settings-Wechsel; Ordnerwechsel leert die Auswahl. Modifier per
   `QApplication.keyboardModifiers`-Seam mockbar.
5. **Heatmap-Marker:** `heatmap_canvas`-Test — bei nicht-leerem `selected` ein
   zusätzlicher Ring-Scatter mit der erwarteten Farbe/Position.
6. **Ausgrauen:** `control_panel`-Test — `show_histogram=False` ⇒
   `_bins.isEnabled()` und `_histogram_stats.isEnabled()` sind False.

Gesamte Suite (`pytest`) muss grün bleiben; bestehende Spektrum-/Heatmap-Tests
ggf. an die neuen Signaturen anpassen.

## Versionierung

Nutzer-sichtbare Feature-Erweiterung → MINOR-Bump auf **0.7.0** nach
Abschluss (pyproject.toml, README-Badge, uv.lock, Tag `v0.7.0`).
