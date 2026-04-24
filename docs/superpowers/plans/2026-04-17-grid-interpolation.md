# Interpoliertes Heatmap-Raster Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Räumlich interpolierte Heatmap, bei der alle Zellen innerhalb der Messpunkte eine Farbe erhalten, ergänzt durch Marker an echten Messpositionen und eine wählbare Farbskala.

**Architecture:** `build_grid` liefert weiterhin ein sparse Grid (NaN für fehlende Zellen). Eine neue Funktion `interpolate_grid` in `processing.py` füllt das Grid per `scipy.interpolate.griddata(method='linear')`. `make_heatmap` in `app.py` erhält zusätzliche Parameter für Farbskala und Messpunkt-Marker (separater `go.Scatter`-Trace).

**Tech Stack:** Python, NumPy, SciPy (`scipy.interpolate.griddata`), Plotly (`go.Heatmap`, `go.Scatter`), Streamlit

---

## File Map

| Datei | Änderung |
|---|---|
| `requirements.txt` | `scipy>=1.12.0` hinzufügen |
| `processing.py` | Neue Funktion `interpolate_grid` + `from scipy.interpolate import griddata` |
| `tests/test_processing.py` | Tests für `interpolate_grid` |
| `app.py` | Sidebar-Selectbox, `interpolate_grid`-Aufruf, neue `make_heatmap`-Signatur mit Marker-Overlay |

---

## Task 1: scipy-Abhängigkeit hinzufügen

**Files:**
- Modify: `requirements.txt`
- Modify: `processing.py` (Import)

- [ ] **Step 1: scipy zu requirements.txt hinzufügen**

Datei `requirements.txt` nach Bearbeitung:
```
streamlit>=1.35.0
plotly>=5.18.0
pandas>=2.1.0
numpy>=1.26.0
scipy>=1.12.0
pytest>=8.0.0
```

- [ ] **Step 2: Import in processing.py ergänzen**

Am Anfang von `processing.py` nach `import numpy as np` einfügen:
```python
from scipy.interpolate import griddata
```

- [ ] **Step 3: Installation prüfen**

```bash
pip install scipy
python -c "from scipy.interpolate import griddata; print('OK')"
```
Expected: `OK`

- [ ] **Step 4: Commit**

```bash
git add requirements.txt processing.py
git commit -m "chore: add scipy dependency for grid interpolation"
```

---

## Task 2: `interpolate_grid` TDD

**Files:**
- Modify: `tests/test_processing.py`
- Modify: `processing.py`

- [ ] **Step 1: Fehlschlagende Tests schreiben**

Am Ende von `tests/test_processing.py` anhängen:

```python
from processing import interpolate_grid


def test_interpolate_grid_fills_interior():
    # 3x3 Grid: Werte an allen 4 Ecken, Mitte und Kanten fehlen
    # Linear interpoliert: Zentrum (1,1) soll ~2.0 sein (Mittel der Ecken)
    grid = np.array([
        [1.0, np.nan, 3.0],
        [np.nan, np.nan, np.nan],
        [1.0, np.nan, 3.0],
    ])
    result = interpolate_grid(grid)
    assert not np.isnan(result[1, 1])
    assert np.isclose(result[1, 1], 2.0, atol=0.1)


def test_interpolate_grid_preserves_known_values():
    grid = np.array([
        [1.0, np.nan, 3.0],
        [np.nan, np.nan, np.nan],
        [1.0, np.nan, 3.0],
    ])
    result = interpolate_grid(grid)
    assert np.isclose(result[0, 0], 1.0)
    assert np.isclose(result[0, 2], 3.0)


def test_interpolate_grid_outside_convex_hull_is_nan():
    # Nur 3 Punkte im Zentrum — Ecken liegen außerhalb der konvexen Hülle
    grid = np.full((5, 5), np.nan)
    grid[2, 1] = 1.0
    grid[2, 3] = 2.0
    grid[3, 2] = 3.0
    result = interpolate_grid(grid)
    assert np.isnan(result[0, 0])
    assert np.isnan(result[4, 4])


def test_interpolate_grid_too_few_points_returns_copy():
    # Weniger als 3 Messpunkte: keine Interpolation möglich, Grid unverändert zurück
    grid = np.full((3, 3), np.nan)
    grid[1, 1] = 5.0
    result = interpolate_grid(grid)
    assert np.isclose(result[1, 1], 5.0)
    assert np.isnan(result[0, 0])


def test_interpolate_grid_no_nan_unchanged():
    # Vollständig befülltes Grid bleibt unverändert
    grid = np.array([[1.0, 2.0], [3.0, 4.0]])
    result = interpolate_grid(grid)
    assert np.allclose(result, grid)
```

- [ ] **Step 2: Tests ausführen — müssen fehlschlagen**

```bash
cd /Users/dniehof/Programming/acc_visualisation
pytest tests/test_processing.py -k "interpolate" -v
```
Expected: `ImportError: cannot import name 'interpolate_grid'`

- [ ] **Step 3: `interpolate_grid` implementieren**

In `processing.py` ans Ende (nach `build_grid`) einfügen:

```python
def interpolate_grid(grid: np.ndarray) -> np.ndarray:
    known_mask = ~np.isnan(grid)
    if known_mask.sum() < 3:
        return grid.copy()

    nrows, ncols = grid.shape
    rows, cols = np.mgrid[0:nrows, 0:ncols]

    points = np.column_stack([rows[known_mask], cols[known_mask]])
    values = grid[known_mask]

    return griddata(points, values, (rows, cols), method="linear")
```

- [ ] **Step 4: Tests ausführen — müssen bestehen**

```bash
pytest tests/test_processing.py -k "interpolate" -v
```
Expected: 5 passed

- [ ] **Step 5: Alle Tests ausführen — kein Regressionen**

```bash
pytest tests/ -v
```
Expected: alle Tests grün

- [ ] **Step 6: Commit**

```bash
git add processing.py tests/test_processing.py
git commit -m "feat: add interpolate_grid using scipy linear griddata"
```

---

## Task 3: `make_heatmap` aktualisieren + Sidebar-Selectbox

**Files:**
- Modify: `app.py`

- [ ] **Step 1: Sidebar-Selectbox hinzufügen**

In `app.py`, im `with st.sidebar:` Block, nach dem `shared_scale`-Checkbox einfügen:

```python
colorscale = st.selectbox(
    "Farbskala",
    ["Viridis", "Plasma", "Hot", "RdBu", "Cividis", "Turbo", "Inferno"],
)
```

- [ ] **Step 2: `make_heatmap`-Signatur und Implementierung ersetzen**

Die bestehende `make_heatmap`-Funktion (Zeilen 77–97 in `app.py`) komplett ersetzen:

```python
def make_heatmap(
    grid: np.ndarray,
    title: str,
    use_shared: bool,
    normalized: bool,
    colorscale: str,
    hole_positions: list[tuple[int, int]],
    hole_values: list[float],
) -> go.Figure:
    nrows, ncols = grid.shape
    fig = go.Figure(
        go.Heatmap(
            z=grid,
            x=list(range(1, ncols + 1)),
            y=list(range(1, nrows + 1)),
            colorscale=colorscale,
            zmin=z_min if use_shared else None,
            zmax=z_max if use_shared else None,
            colorbar=dict(title="Normalisiert" if normalized else "g RMS"),
            hoverongaps=False,
        )
    )
    label = "Normalisiert" if normalized else "g RMS"
    fig.add_trace(go.Scatter(
        x=[y for (_, y) in hole_positions],
        y=[x for (x, _) in hole_positions],
        mode="markers",
        marker=dict(
            size=8,
            color="rgba(255,255,255,0.4)",
            line=dict(color="rgba(0,0,0,0.7)", width=1.5),
        ),
        customdata=hole_values,
        hovertemplate=f"x=%{{y}}, y=%{{x}}<br>{label}=%{{customdata:.4f}}<extra></extra>",
        showlegend=False,
    ))
    fig.update_layout(
        title=title,
        xaxis_title="y-Bohrung",
        yaxis_title="x-Bohrung",
        height=500,
    )
    return fig
```

Hinweis zu Koordinaten: In `hole_positions` sind Tupel `(x_bohrung, y_bohrung)`. Im Plotly-Heatmap ist die horizontale Achse `y-Bohrung` (= `x` im Scatter) und die vertikale Achse `x-Bohrung` (= `y` im Scatter).

- [ ] **Step 3: Commit**

```bash
git add app.py
git commit -m "feat: update make_heatmap with colorscale param and measurement markers"
```

---

## Task 4: Interpolation in App-Pipeline einbinden

**Files:**
- Modify: `app.py`

- [ ] **Step 1: Import ergänzen**

Am Anfang von `app.py` nach `from processing import build_grid, compute_band_rms`:
```python
from processing import build_grid, compute_band_rms, interpolate_grid
```

- [ ] **Step 2: Interpolierte Grids berechnen**

Nach dem bestehenden `# --- Build grids ---` Block (nach Zeile 69) einfügen:

```python
# --- Interpolate grids ---
interp_grids: dict[str, np.ndarray] = {
    name: interpolate_grid(g) for name, g in grids.items()
}
```

- [ ] **Step 3: Shared colour scale auf Basis der originalen Grids belassen**

Die bestehende Berechnung von `z_min`/`z_max` (Zeilen 72–74) bleibt unverändert — sie verwendet weiterhin `grids` (sparse), da interpolierte Werte per Definition zwischen gemessenem Min und Max liegen.

- [ ] **Step 4: Render-Loop auf interpolierte Grids + neue Signatur umstellen**

Den bestehenden Render-Loop (ab `for col, name in zip(cols, plate_names):`) so anpassen:

```python
for col, name in zip(cols, plate_names):
    with col:
        ref_val = ref_rms_values.get(name)
        if ref_val is not None:
            label = "Normalisiert (Ref = 1.0)" if normalize else f"{ref_val:.4f} g RMS"
            st.metric(f"{name} — Referenz", label)

        hole_data_plate, _ = plates[name]
        sparse_grid = grids[name]
        positions = list(hole_data_plate.keys())  # [(x_bohrung, y_bohrung), ...]
        values = [
            float(sparse_grid[x - 1, y - 1])
            for (x, y) in positions
            if not np.isnan(sparse_grid[x - 1, y - 1])
        ]
        positions_valid = [
            (x, y) for (x, y) in positions
            if not np.isnan(sparse_grid[x - 1, y - 1])
        ]

        fig = make_heatmap(
            interp_grids[name],
            name,
            shared_scale,
            normalize,
            colorscale,
            positions_valid,
            values,
        )
        event = st.plotly_chart(fig, on_select="rerun", key=f"heatmap_{name}", use_container_width=True)
        clicked = None
        if event and event["selection"] and event["selection"]["points"]:
            pt = event["selection"]["points"][0]
            clicked = (int(pt["y"]), int(pt["x"]))  # (x_hole, y_hole)
        click_state[name] = clicked
```

- [ ] **Step 5: App manuell testen**

```bash
streamlit run app.py
```

Prüfen:
- Heatmap zeigt interpolierte Farben zwischen Messpunkten
- Messpunkte sind mit halbtransparenten Kreisen markiert
- Hover auf Marker zeigt echten RMS-Wert
- Farbskala-Selectbox in Sidebar wechselt die Farbe korrekt
- Klick auf Bohrung öffnet Spektrum-Detail wie zuvor
- Gemeinsame Farbskala funktioniert bei zwei Platten

- [ ] **Step 6: Commit**

```bash
git add app.py
git commit -m "feat: wire interpolate_grid into app pipeline with colorscale selector"
```
