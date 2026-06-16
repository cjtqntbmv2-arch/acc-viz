# Beschleunigungs-Visualisierung — Desktop-App

Native PySide6/Qt-Anwendung zur Auswertung von **Beschleunigungs-PSD-Messungen
an Plattenbohrungen**. Für eine oder zwei Platten parallel berechnet das
Programm pro Bohrung den **Band-RMS** (Integration der PSD über ein wählbares
Frequenzband) und stellt ihn als Heatmap, Histogramm und PSD-Spektrum dar.

> Diese Anleitung ist auch in der App über **Hilfe → Anleitung** abrufbar.

## Quick Guide

1. **Starten** — `python3 desktop_main.py` (im Projektordner, mit aktiviertem `.venv`).
2. **Ordner wählen** — im linken Panel **„Einstellungen"** bei
   **„Platte 1 — Ordnerpfad"** über 📁 (**„Ordner wählen"**) oder per Pfadeingabe
   den Messordner setzen. **„Platte 2 — Ordnerpfad (optional)"** ist optional.
   Die Auswertung startet automatisch.
3. **Einstellungen anpassen** — jede Änderung aktualisiert die Anzeige sofort
   (siehe Funktionsreferenz).
4. **Spektrum ansehen** — in der Heatmap auf einen weißen Kreis (gemessene
   Bohrung) klicken; das PSD-Spektrum erscheint unterhalb der Platten.
5. **Exportieren** — in der Werkzeugleiste **„CSV exportieren"** klicken und den
   Speicherort wählen.

## Workflow

1. Pro Platte einen Ordner mit den Bohrungs-CSVs (und optional `Referenz.csv`)
   bereitstellen.
2. Platte 1 (und optional Platte 2) laden.
3. **Frequenzband (Hz)** und **Achse** für die gewünschte Auswertung setzen.
4. Für den direkten Vergleich zweier Platten **„Normalisiert (relativ zur
   Referenz)"** und **„Gemeinsame Farbskala"** aktivieren.
5. **Interpolation** und **Interpolations-Methode** nach Datenlage wählen.
6. Heatmap und Histogramm ablesen; bei Auffälligkeiten per Klick ins
   **Spektrum** einer Bohrung drillen.
7. Ergebnis über **„CSV exportieren"** sichern.

## Eingabedaten

Pro Platte ein Ordner mit:

- **Bohrungsmessungen**: CSV-Dateien `x{N}-y{M}.csv` (z. B. `x0-y3.csv`,
  case-insensitiv, 0-indizierte Koordinaten) mit den Spalten `Frequenz_Hz`,
  `PSD_X_g2Hz`, `PSD_Y_g2Hz`, `PSD_Z_g2Hz`.
- **Referenzmessung** (optional): `Referenz.csv` mit gleichem Schema —
  Voraussetzung für Normalisierung und Referenz-Stern.

## Funktionsreferenz

Bedienelemente im Panel **„Einstellungen"** (von oben nach unten):

- **Platte 1 — Ordnerpfad** / **Platte 2 — Ordnerpfad (optional)** — Messordner
  per 📁 **„Ordner wählen"** oder direkter Pfadeingabe. Platte 1 ist Pflicht,
  Platte 2 optional.
- **Frequenzband (Hz)** — Bereich `f_min`–`f_max` (0–25 000 Hz, Schrittweite
  100 Hz), über den der Band-RMS integriert wird. `f_min` bleibt stets
  mindestens 100 Hz kleiner als `f_max` (automatisch erzwungen). Wirkt auf
  Heatmap, Spektrum-Hervorhebung und CSV-Export.
- **Achse** — `X`, `Y`, `Z` einzeln oder `RSS` = √(gRMS_X² + gRMS_Y² + gRMS_Z²),
  die Root Sum of Squares der drei Achsen (richtungsunabhängige Gesamtbelastung).
- **Normalisiert (relativ zur Referenz)** — teilt jeden Bohrungs-RMS durch den
  Referenz-RMS derselben Platte; Ergebnis dimensionslos, Referenz = 1,0.
  Erfordert `Referenz.csv`.
- **Interpolation** — füllt fehlende Rasterzellen. Deaktiviert: nur gemessene
  Zellen werden angezeigt. Standard: aktiv.
- **Interpolations-Methode** — **„Linear (Delaunay)"** (schnell, zeigt
  Dreiecks-Facetten, bricht bei kollinearen Messpunkten ab) oder
  **„Thin-Plate-Spline"** (glatte Fläche, robust bei wenigen/kollinearen
  Punkten). Nur aktiv, wenn Interpolation eingeschaltet ist.
- **Histogramm-Bins** — Anzahl der Bins (5–50); wird automatisch auf die Anzahl
  gemessener Löcher reduziert, falls diese kleiner ist.
- **Statistik anzeigen** — blendet Mittelwert (µ), Median und ±1σ als Linien mit
  Zahlenwerten im Histogramm ein.
- **Gemeinsame Farbskala** — alle Heatmaps nutzen denselben zmin/zmax-Bereich
  (erleichtert den direkten Platten-Vergleich).
- **Farbskala** — Farbpalette der Heatmap. Viridis/Cividis sind perzeptuell
  gleichmäßig (empfohlen), RdBu betont Abweichungen.

Werkzeugleiste:

- **CSV exportieren** — schreibt pro Bohrung eine Zeile mit absolutem und
  normalisiertem Band-RMS für das aktuell gewählte Frequenzband und die Achse.
  Format: UTF-8 mit BOM, Semikolon-getrennt (Excel-kompatibel). Standardname
  `beschleunigung_export.csv`.

## Darstellung verstehen

- **Heatmap** (pro Platte) — räumliche Verteilung des Band-RMS über das
  Bohrungsraster (Achsen **x-Bohrung** / **y-Bohrung**). **Weiße Kreise**
  markieren gemessene Bohrungen (anklickbar fürs Spektrum), ein **gelber Stern**
  den Referenzwert in der Plattenmitte. Fehlende Zellen werden bei aktiver
  Interpolation gefüllt.
- **Histogramm** (pro Platte) — Verteilung der Bohrungswerte (Achse
  **Anzahl Löcher**), optional mit µ, Median und ±1σ.
- **Spektrum-Drilldown** — PSD über der Frequenz für die angeklickte Bohrung,
  inklusive Referenzkurve und hervorgehobenem Frequenzband; bei Achse `RSS`
  zusätzlich die Summenkurve X+Y+Z.
- **Referenz-Metrik** — pro Platte wird der Referenz-RMS im aktuellen
  Frequenzband angezeigt (bzw. „Normalisiert (Ref = 1.0)" im Normalisiert-Modus).

## Fehlermeldungen

Lade- und Datenfehler erscheinen in der Statusleiste bzw. als Hinweis im
Inhaltsbereich, u. a.:

- Pfad existiert nicht / Pfad ist kein Ordner.
- Ordner enthält keine Dateien im Format `x{N}-y{M}.csv`.
- CSV konnte nicht gelesen werden (Encoding/Trennzeichen unbekannt).
- Spalten fehlen (erwartet: `Frequenz_Hz, PSD_X_g2Hz, PSD_Y_g2Hz, PSD_Z_g2Hz`).
- Datei enthält keine auswertbaren Messwerte.

## Start & Entwicklung

- Desktop-App: `python3 desktop_main.py`
- Tests: `.venv/bin/python -m pytest`
- Native `.app`/`.exe` via PyInstaller: siehe [packaging/](packaging/).
