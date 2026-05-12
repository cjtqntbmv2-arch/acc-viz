# Interpolation-Toggle (Sidebar)

## Kontext

Die Heatmap füllt fehlende Zellen aktuell immer per `interpolate_grid`
(lineare Triangulation + Nearest-Neighbour-Fallback). Es gibt Situationen,
in denen der Nutzer ausschließlich die tatsächlich gemessenen Werte sehen
will — z. B. um interpolierte Bereiche nicht mit echten Messwerten zu
verwechseln, oder bei degenerierten Punktekonfigurationen (kollineare
Lochpositionen), bei denen die Interpolation einen Qhull-Fehler werfen
kann. Ein Sidebar-Toggle stellt diese Option bereit.

## Verhalten

- **Label**: "Interpolation"
- **Default**: an (aktuelles Verhalten unverändert)
- **Aus**: Heatmap zeigt das rohe `grids[name]`. NaN-Zellen werden dank
  `hoverongaps=False` von Plotly transparent gerendert. Die gemessenen
  Lochpositionen bleiben über die bestehenden `hole_positions` /
  `hole_values` als Marker sichtbar.
- **An**: Bisheriges Verhalten — `interpolate_grid` mit Referenzwert.

## Änderungen

### `src/ui/strings.py`
Neue Konstanten:
- `INTERPOLATE = "Interpolation"`
- `HELP_INTERPOLATE = "Wenn deaktiviert, werden nur die gemessenen Zellen angezeigt; fehlende Zellen bleiben leer."`

### `src/ui/sidebar.py`
- `Settings` um Feld `interpolate: bool` erweitern (nach `normalize`,
  in Reihenfolge im Dataclass und im Konstruktor-Aufruf).
- In `render_sidebar()` zwischen den bestehenden `normalize`- und
  `shared_scale`-Widgets:
  ```python
  interpolate = st.toggle(S.INTERPOLATE, value=True, help=S.HELP_INTERPOLATE)
  ```
- Wert im `Settings(...)`-Aufruf durchreichen.

### `app.py` (Zeile 95)
Ersetzen:
```python
interp_grids = {name: interpolate_grid(g, _ref_for_interp(name)) for name, g in grids.items()}
```
durch:
```python
if settings.interpolate:
    interp_grids = {name: interpolate_grid(g, _ref_for_interp(name)) for name, g in grids.items()}
else:
    interp_grids = {name: g.copy() for name, g in grids.items()}
```

## Tests

- Falls `tests/ui/test_sidebar.py` existiert: Default-Wert (`interpolate is True`) und Toggle-Verhalten ergänzen.
- Smoke-Test: `Settings`-Instanziierung mit `interpolate=False` schlägt nicht fehl.

## Verifikation

1. `python3 -m streamlit run app.py`
2. Daten laden, Heatmap erscheint mit Interpolation (Default).
3. Toggle "Interpolation" deaktivieren: nur die Messzellen sind gefärbt,
   übrige Zellen transparent. Loch-Marker und Referenz-Stern bleiben sichtbar.
4. Toggle wieder aktivieren: vollflächig interpolierte Heatmap erscheint.

## Nicht-Ziele

- Kein Caching-Refactor für `interp_grids`.
- Keine Änderung an `interpolate_grid` oder am Qhull-Fehler-Handling.
