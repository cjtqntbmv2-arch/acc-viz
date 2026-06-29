# Beschleunigungs-Visualisierung

Desktop-App (PySide6) zur Auswertung und Visualisierung von
Beschleunigungs-PSD-Messungen an Messpunkten auf Platten.

## Input

- **Ordner pro Platte** (1–2 Platten parallel) mit:
  - **Messpunkt-Messungen**: CSV-Dateien `x{N}-y{M}.csv` (0-indizierte Koordinaten)
    - Spalten: `Frequenz_Hz`, `PSD_X_g2Hz`, `PSD_Y_g2Hz`, `PSD_Z_g2Hz`
  - **Referenzmessung** (optional): `Referenz.csv` mit gleichem Schema
- **UI-Einstellungen** (Bedienpanel):
  - Frequenzband `[f_min, f_max]` in Hz
  - Achse: `X` / `Y` / `Z` / `RSS` (Root Sum of Squares)
  - Normalisierung relativ zur Referenz (Toggle)
  - Interpolation an/aus (Toggle)
  - Gemeinsame Farbskala über beide Platten (Toggle)
  - Farbskala

## Funktion

1. **Laden**: CSVs pro Messpunkt und Referenz einlesen, Schema validieren.
2. **Band-RMS**: Pro Messpunkt wird der RMS der gewählten Achse über `[f_min, f_max]`
   aus der PSD integriert (`compute_band_rms`).
3. **Grid-Aufbau**: Werte werden in ein 2D-Array `(max_x+1, max_y+1)` einsortiert
   (NaN für fehlende Messpunkte).
4. **Optional Normalisierung**: jeder Messpunkt wird durch den Referenz-RMS geteilt.
5. **Optional Interpolation**: fehlende Zellen werden per linearer Triangulation
   + Nearest-Neighbour-Fallback gefüllt; bei deaktiviertem Toggle bleiben sie leer.
6. **Heatmap-Anzeige**: pro Platte eine matplotlib-Heatmap mit
   Messpunktmarkern und Referenz-Stern in Plattenmitte.
7. **Spektrum-Drilldown**: Klick auf einen Messpunkt zeigt das PSD-Spektrum.
   Per **Strg/Cmd-Klick** lassen sich mehrere Messpunkte auswählen und im
   Spektrum überlagern (auch plattenübergreifend); die gewählten Messpunkte
   werden auf der Heatmap farblich markiert.

## Output

- **Heatmaps** der Band-RMS-Verteilung pro Platte (matplotlib).
- **Referenz-Metric** (Stern + Wert) pro Platte.
- **PSD-Spektrum** der ausgewählten Messpunkte (mit Referenzkurve bei
  Einzelauswahl, hervorgehobenes Band).
- **CSV-Export**: pro Messpunkt eine Zeile mit absolutem und normalisiertem
  Band-RMS für aktuelles Frequenzband und Achse (UTF-8 BOM, Semikolon).

## Start

```bash
python3 desktop_main.py
```
