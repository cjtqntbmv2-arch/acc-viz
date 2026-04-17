# Design: Interpoliertes Heatmap-Raster

**Datum:** 2026-04-17  
**Status:** Approved

## Ziel

Die aktuelle Heatmap zeigt nur gemessene Bohrungspositionen mit Farbe; nicht gemessene Zellen sind leer (NaN). Ziel ist eine räumlich interpolierte Darstellung, bei der alle Zellen innerhalb der Messpunkte eine Farbe erhalten, ergänzt durch Marker an den echten Messpositionen und eine wählbare Farbskala.

## Datenverarbeitung

### Neue Funktion `interpolate_grid` in `processing.py`

```python
def interpolate_grid(grid: np.ndarray) -> np.ndarray
```

- Nimmt das sparse Grid aus `build_grid` (NaN für nicht gemessene Zellen)
- Extrahiert alle bekannten Messpunkte (Koordinaten + Werte)
- Ruft `scipy.interpolate.griddata(points, values, xi, method='linear')` auf dem vollen Gitter auf
- Zellen innerhalb der konvexen Hülle der Messpunkte erhalten interpolierte Werte
- Zellen außerhalb bleiben NaN und werden in der Heatmap weiß dargestellt

### Datenpipeline

```
hole_data → build_grid (sparse NaN grid) → interpolate_grid (gefülltes Grid) → make_heatmap
```

### Abhängigkeit

`scipy` wird in `requirements.txt` hinzugefügt.

## Sidebar

Ein neues `st.selectbox("Farbskala", ...)` mit folgenden Optionen:

- Viridis (Standard)
- Plasma
- Hot
- RdBu
- Cividis
- Turbo
- Inferno

Der gewählte Wert wird als `colorscale: str` an `make_heatmap` übergeben.

## Heatmap-Darstellung (`make_heatmap`)

### Signatur-Erweiterung

```python
def make_heatmap(
    grid: np.ndarray,
    title: str,
    use_shared: bool,
    normalized: bool,
    colorscale: str,
    hole_positions: list[tuple[int, int]],
    hole_values: list[float],
) -> go.Figure
```

### Interpolierte Heatmap

- `go.Heatmap` mit dem interpolierten Grid (kein NaN im Inneren)
- `colorscale` wird aus dem Sidebar-Parameter gesetzt (nicht mehr hartcodiert `"Viridis"`)
- `hoverongaps=False` bleibt erhalten
- Hover zeigt den interpolierten Wert

### Messpunkt-Marker

- `go.Scatter`-Spur wird auf der Heatmap überlagert
- Marker: kleiner Kreis mit dunklem Rand, halbtransparente Füllung
- Positionen: tatsächliche Bohrungskoordinaten aus `hole_positions`
- Hover zeigt den **echten gemessenen** RMS-Wert aus `hole_values`
- Marker-Spur hat `showlegend=False`

### Klick-Verhalten

Unverändert — Klick auf einen Punkt löst die Spektrum-Detailansicht aus.

## Nicht im Scope

- Änderung der Klick-Logik oder Spektrum-Darstellung
- Marker-Beschriftung als permanenter Text (nur Hover)
- Kubische oder andere Interpolationsmethoden (kein UI-Toggle)
