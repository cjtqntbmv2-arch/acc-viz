# Acc Visualisation — Design Spec

**Datum:** 2026-04-17

## Kontext

Zwei Metallplatten (22×22 und 29×29 Bohrungsraster) wurden mit einem dreiachsigen Beschleunigungsaufnehmer vermessen. Pro Bohrung liegt ein PSD-Spektrum (Power Spectral Density) für die Achsen X, Y, Z vor — gespeichert als einzelne CSV-Datei (`x{n}-y{m}.csv`). In der geometrischen Mitte jeder Platte wurde eine Referenzmessung (`Referenz.csv`) aufgenommen.

Ziel: Eine interaktive Streamlit-App, die die Beschleunigungsverteilung als Heatmap visualisiert, den Frequenzband-RMS wählbar macht, die Normalisierung zur Referenz ermöglicht und die Ergebnisse als CSV exportiert.

---

## Dateiformat

- **Header:** 11 Kommentarzeilen (`# ...`)
- **Spalten:** `Frequenz_Hz, PSD_X_g2Hz, PSD_Y_g2Hz, PSD_Z_g2Hz`
- **Frequenzauflösung:** 0.3815 Hz (konstant, aus Header lesbar)
- **Dateinamen:** `x{n}-y{m}.csv` (1-basierte Indizierung), Referenz: `Referenz.csv`
- **Teilmessungen:** Fehlende Dateien ergeben NaN in der Heatmap

---

## Architektur

```
acc_visualisation/
├── app.py              # Streamlit-Einstiegspunkt
├── data_loader.py      # CSV-Parsing, Datei-Erkennung, Caching
├── processing.py       # Band-RMS-Berechnung, Normalisierung, Grid-Aufbau
└── requirements.txt
```

### `data_loader.py`

- Scannt Ordner nach `x{n}-y{m}.csv` per Regex
- Liest Header (11 Zeilen) und extrahiert `Frequenzauflösung` als float
- Gibt zurück: `dict[(x, y) -> DataFrame]` + `ref_df: DataFrame`
- Gecacht via `@st.cache_data` (Key: Ordnerpfad + Datei-Mtimes)

### `processing.py`

- `compute_band_rms(df, f_min, f_max, axis)` → float
  - Filtert Zeilen: `f_min <= Frequenz_Hz <= f_max`
  - `sqrt(sum(PSD * delta_f))`
- `build_grid(hole_data, ref_df, f_min, f_max, axis, normalize)` → 2D np.ndarray
  - Bestimmt Gittergröße aus max(x), max(y) in `hole_data`
  - Füllt NaN für fehlende Bohrungen

### `app.py`

- Lädt Daten bei Ordnerauswahl
- Rendert Sidebar + Heatmap(s) + Spektrum-Detail + CSV-Export

---

## UI-Layout

### Sidebar

| Steuerelement | Typ | Details |
|---|---|---|
| Platte 1 — Ordnerpfad | Texteingabe | Optional |
| Platte 2 — Ordnerpfad | Texteingabe | Optional |
| Frequenzband | Doppelschieberegler | 0–25000 Hz |
| Achse | Radio-Buttons | X / Y / Z |
| Darstellung | Toggle | Absolut / Normalisiert |
| Farbskala | Checkbox | Gemeinsam / Individuell |
| CSV-Export | Button | — |

Mindestens ein Ordnerpfad muss gesetzt sein. Ist nur einer gesetzt, wird eine Heatmap in voller Breite gezeigt; sind beide gesetzt, erscheinen sie nebeneinander.

### Hauptbereich

- **Kennzahl:** Referenz-Band-RMS über jeder Heatmap (z.B. `Ref: 3.21 g RMS`)
- **Heatmap:** Plotly `go.Heatmap`, NaN-Felder grau
- **Spektrum-Detail:** Klick auf Bohrung (via `streamlit-plotly-events`) → Plotly-Liniendiagramm darunter: gewählte Bohrung (farbig) vs. Referenz (grau), logarithmische Y-Achse (PSD), lineares X (Frequenz)

---

## Berechnungslogik

**Band-RMS:**
```
band_rms = sqrt( Σ PSD[i] * Δf )   für alle f[i] ∈ [f_min, f_max]
```

**Normalisierung:**
```
band_rms_normalized = band_rms_hole / band_rms_reference
```
Der Referenz-Band-RMS wird mit denselben f_min/f_max berechnet.

---

## CSV-Export

Format (eine Zeile pro Bohrung und Platte):

```
plate,x,y,axis,f_min_hz,f_max_hz,band_rms_abs,band_rms_normalized
HALT1,1,1,X,100,5000,2.34,0.95
HALT1,1,2,X,100,5000,2.41,0.98
...
```

`band_rms_normalized` ist leer (`""`), wenn keine Referenzdatei vorhanden.

---

## Abhängigkeiten (`requirements.txt`)

```
streamlit
plotly
pandas
numpy
streamlit-plotly-events
```

---

## Verifikation

1. App starten: `streamlit run app.py`
2. Ordner `HALT1/` laden → 7 Bohrungen erscheinen, Rest grau
3. Frequenzband verschieben → Heatmap-Werte aktualisieren sich
4. Achse wechseln → Heatmap ändert sich
5. Absolut ↔ Normalisiert → Werte ändern sich, Referenz-Kennzahl bleibt konstant
6. Klick auf Bohrung → PSD-Spektrum erscheint darunter
7. CSV-Export → Datei enthält korrekte Spalten und Werte
8. Zweiten Ordner leer lassen → nur eine Heatmap, volle Breite
