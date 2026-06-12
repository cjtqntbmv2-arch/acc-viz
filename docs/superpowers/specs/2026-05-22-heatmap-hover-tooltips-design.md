# Design: Heatmap-Hover-Tooltips (Desktop-Frontend)

## Context

Das native PySide6-Desktop-Frontend (`src/desktop`) bildet das Streamlit/Plotly-Frontend
nach. Die Plotly-Heatmap (`src/ui/heatmap.py`) zeigt beim Hovern Tooltips auf drei
Element-Typen — die matplotlib-Desktop-Heatmap (`src/desktop/plots/heatmap_canvas.py`)
hat bisher **keine** Hover-Tooltips, nur Klick → Spektrum. Diese Lücke soll geschlossen
werden (volle Parität zu Plotly):

| Element | Plotly-`hovertemplate` | Anzeige |
|---|---|---|
| Messpunkt-Marker | `x=…, y=…<br>{label}=%{customdata:.4f}` | Koordinaten + gemessener gRMS |
| Zelle (interpoliert) | `x=…, y=…<br>Interpoliert ({label})=%{z:.4f}` | Koordinaten + interpolierter Wert |
| Referenz-Stern (Mitte) | `Referenz (Mitte)<br>{label}=%{customdata:.4f}` | Referenzwert |

`label` = `S.COLORBAR_NORMALIZED` ("Normalisiert") oder `S.COLORBAR_ABSOLUTE` ("g RMS"),
je nach `normalized`. Gaps/NaN-Zellen zeigen keinen Tooltip (Plotly: `hoverongaps=False`).

## Approach

**Darstellung: Qt-`QToolTip`.** Ein `motion_notify_event`-Handler ermittelt das Element
unter dem Cursor und zeigt per `QToolTip.showText(QCursor.pos(), text, self)` eine native
Box; ist nichts getroffen, `QToolTip.hideText()`. **Kein Figure-Neuzeichnen** bei
Mausbewegung → performant, minimaler Code. (Verworfen: matplotlib-Annotation-Artist —
mehr Code + gezieltes Redraw nötig; `mplcursors` — unnötige neue Abhängigkeit.)

**Erkennung als reine, testbare Funktion.** Messpunkte sitzen exakt auf
Ganzzahl-Koordinaten, daher reicht „Cursor auf nächste Zelle runden" (vorhandenes
`nearest_cell`) statt fragiler Artist-Treffertests:

```python
def resolve_hover(
    xdata: float | None,
    ydata: float | None,
    *,
    grid: np.ndarray,                       # interpolierter Grid, shape (nrows, ncols)
    hole_lookup: dict[tuple[int, int], float],
    ref_value: float | None,
    normalized: bool,
) -> str | None:
    """Tooltip-Text für die Cursorposition, oder None (= ausblenden)."""
```

Priorität (oben gewinnt):
1. **Referenz** — `ref_value is not None` und Cursor nahe Mitte
   `((nrows-1)/2, (ncols-1)/2)` (euklidischer Abstand < 0.5). Der Stern liegt oben auf.
2. **Messpunkt** — gerundete Zelle `(x, y)` in `hole_lookup` → gemessener gRMS.
3. **Interpolierte Zelle** — sonst, wenn `grid[x, y]` endlich.
4. **None** — außerhalb des Grids oder NaN/Gap.

`nearest_cell` liefert bereits Bounds-Checking und das `(x, y)`-Snapping.

## Components

**`src/desktop/plots/heatmap_canvas.py`** (Hauptänderung):
- Modulfunktion `resolve_hover(...)` (rein, oben spezifiziert) — neben `nearest_cell`.
- `render_grid` legt zusätzlich auf der Instanz ab (für den Handler):
  `self._grid` (das übergebene interpolierte Grid), `self._hole_lookup`
  (`dict(zip(hole_positions, hole_values))`), `self._ref_value`, `self._normalized`.
- `__init__`: `self.mpl_connect("motion_notify_event", self._on_motion)`.
- `_on_motion(event)`: außerhalb der Achse → `QToolTip.hideText()`; sonst
  `text = resolve_hover(event.xdata, event.ydata, …)`; `text` → `QToolTip.showText(
  QCursor.pos(), text, self)`, sonst `hideText()`. Klein-Optimierung: nur
  `showText` aufrufen, wenn sich `text` ggü. letztem Wert ändert (Member `self._last_hover`).

**`src/ui/strings.py`** (neue Konstanten, analog zu den Plotly-Texten; `\n` statt `<br>`):
```python
HEATMAP_HOVER_MEASURED = "x={x}, y={y}\n{label}={value:.4f}"
HEATMAP_HOVER_INTERPOLATED = "x={x}, y={y}\nInterpoliert ({label})={value:.4f}"
HEATMAP_HOVER_REFERENCE = "Referenz (Mitte)\n{label}={value:.4f}"
```
`resolve_hover` wählt `label = S.COLORBAR_NORMALIZED if normalized else S.COLORBAR_ABSOLUTE`.

Keine Änderung an `main_window.py` nötig — `render_grid` bekommt `hole_positions`/
`hole_values`/`ref_value`/`normalized` bereits übergeben.

## Data Flow

`main_window._render` → `HeatmapCanvas.render_grid(grid=interp_grids[name], hole_positions,
hole_values, ref_value=marker, normalized=settings.normalize, …)` → speichert Hover-Daten →
Maus über Canvas → `_on_motion` → `resolve_hover` → `QToolTip`.

## Error Handling / Edge Cases

- Cursor außerhalb Achse oder `xdata/ydata is None` → Tooltip aus.
- NaN/maskierte Zelle → kein Tooltip (Parität zu `hoverongaps=False`).
- `ref_value is None` (keine Referenz.csv) → kein Referenz-Tooltip; Mitte fällt auf
  Messpunkt/interpolierte Logik zurück.
- Gerade Grid-Dimensionen: Mitte liegt auf Halb-Koordinaten → Abstandsschwelle < 0.5 trifft
  trotzdem zuverlässig, da der Stern dort gezeichnet wird.

## Testing

`tests/desktop/test_heatmap_canvas.py` erweitern:
- **`resolve_hover` (rein, kein Qt-Event):**
  - Messpunkt-Zelle → `HEATMAP_HOVER_MEASURED`-Text mit korrektem Wert/Koordinaten.
  - Nicht-gemessene, endliche Zelle → `HEATMAP_HOVER_INTERPOLATED`-Text.
  - NaN-Zelle → `None`.
  - Außerhalb des Grids → `None`.
  - Cursor nahe Mitte mit `ref_value` → `HEATMAP_HOVER_REFERENCE`; mit `ref_value=None` →
    Fallback auf Mess-/Interpolations-Logik.
  - `normalized=True/False` wählt korrektes `label`.
- **Smoke:** `render_grid` + manueller Aufruf von `_on_motion` mit einem synthetischen
  Event (oder direkt `resolve_hover`) wirft nicht; bestehender Render-Test bleibt grün.

## Verifikation

1. `python3 -m pytest tests/desktop -q` — alle grün.
2. `python3 desktop_main.py`: Platte laden, Maus über Heatmap bewegen:
   - über weißem Messpunkt → `x=…, y=…` + gemessener gRMS,
   - über interpolierter Fläche → `x=…, y=…` + Interpoliert (…),
   - über Mitte/Stern (bei vorhandener Referenz) → Referenz-Wert,
   - über NaN/Rand → kein Tooltip.
