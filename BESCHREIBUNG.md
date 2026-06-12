# Beschleunigungs-Visualisierung

Streamlit-App zur Auswertung und Visualisierung von Beschleunigungs-PSD-Messungen
an Plattenbohrungen.

## Input

- **Ordner pro Platte** (1–2 Platten parallel) mit:
  - **Lochmessungen**: CSV-Dateien `x{N}-y{M}.csv` (0-indizierte Koordinaten)
    - Spalten: `Frequenz_Hz`, `PSD_X_g2Hz`, `PSD_Y_g2Hz`, `PSD_Z_g2Hz`
  - **Referenzmessung** (optional): `Referenz.csv` mit gleichem Schema
- **UI-Einstellungen** (Sidebar):
  - Frequenzband `[f_min, f_max]` in Hz
  - Achse: `X` / `Y` / `Z` / `RSS` (Root Sum of Squares)
  - Normalisierung relativ zur Referenz (Toggle)
  - Interpolation an/aus (Toggle)
  - Gemeinsame Farbskala über beide Platten (Toggle)
  - Plotly-Farbpalette

## Funktion

1. **Laden**: CSVs pro Loch und Referenz einlesen, Schema validieren.
2. **Band-RMS**: Pro Loch wird der RMS der gewählten Achse über `[f_min, f_max]`
   aus der PSD integriert (`compute_band_rms`).
3. **Grid-Aufbau**: Werte werden in ein 2D-Array `(max_x+1, max_y+1)` einsortiert
   (NaN für fehlende Löcher).
4. **Optional Normalisierung**: jedes Loch wird durch den Referenz-RMS geteilt.
5. **Optional Interpolation**: fehlende Zellen werden per linearer Triangulation
   + Nearest-Neighbour-Fallback gefüllt; bei deaktiviertem Toggle bleiben sie leer.
6. **Heatmap-Anzeige**: pro Platte eine Plotly-Heatmap mit
   Lochmarkern und Referenz-Stern in Plattenmitte.
7. **Spektrum-Drilldown**: Klick auf eine Lochzelle zeigt das PSD-Spektrum.

## Output

- **Heatmaps** der Band-RMS-Verteilung pro Platte (interaktiv, Plotly).
- **Referenz-Metric** (Stern + Wert) pro Platte.
- **PSD-Spektrum** des ausgewählten Lochs (mit Referenzkurve, hervorgehobenes Band).
- **CSV-Export**: pro Loch eine Zeile mit absolutem und normalisiertem
  Band-RMS für aktuelles Frequenzband und Achse (UTF-8 BOM, Semikolon).

## Start

```bash
python3 -m streamlit run app.py
```
