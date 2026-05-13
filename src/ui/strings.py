from __future__ import annotations

PAGE_TITLE = "Beschleunigungs-Visualisierung"
APP_TITLE = "Beschleunigungs-Visualisierung — Plattenanalyse"

SIDEBAR_HEADER = "Einstellungen"
FOLDER_PLATE_1 = "Platte 1 — Ordnerpfad"
FOLDER_PLATE_2 = "Platte 2 — Ordnerpfad (optional)"
PICK_FOLDER = "Ordner wählen"

FREQUENCY_BAND = "Frequenzband (Hz)"
AXIS = "Achse"
NORMALIZE = "Normalisiert (relativ zur Referenz)"
INTERPOLATE = "Interpolation"
SHARED_SCALE = "Gemeinsame Farbskala"
COLORSCALE = "Farbskala"

CSV_EXPORT = "CSV exportieren"

LOADING_PLATE = "Lade {label} …"
WAITING_FOR_FOLDER = "Bitte mindestens einen Ordnerpfad eingeben."

ERROR_PATH_NOT_FOUND = "Pfad existiert nicht: {path}"
ERROR_NOT_A_DIR = "Pfad ist kein Ordner: {path}"
ERROR_EMPTY_FOLDER = "Ordner enthält keine Dateien im Format x{{N}}-y{{M}}.csv: {path}"
ERROR_CSV_READ = "CSV konnte nicht gelesen werden — Encoding/Trennzeichen unbekannt: {path}"
ERROR_CSV_SCHEMA = "Spalten fehlen in {path}: {missing}. Erwartet: Frequenz_Hz, PSD_X_g2Hz, PSD_Y_g2Hz, PSD_Z_g2Hz."
ERROR_CSV_CONTENT = "Datei {path} enthält keine auswertbaren Messwerte."
ERROR_GENERIC_PLATE = "{label} konnte nicht geladen werden: {detail}"

REF_METRIC_LABEL_NORMALIZED = "Normalisiert (Ref = 1.0)"
REF_METRIC_LABEL_ABS = "{value:.4f} g RMS"
REF_METRIC_HEADER = "{name} — Referenz"

COLORBAR_NORMALIZED = "Normalisiert"
COLORBAR_ABSOLUTE = "g RMS"

SPECTRUM_TITLE = "{name} — Bohrung ({x}, {y}) · Achse {axis}"
SPECTRUM_X_LABEL = "Frequenz (Hz)"
SPECTRUM_Y_LABEL_TMPL = "PSD {axis} (g²/Hz)"
SPECTRUM_TRACE_HOLE = "Bohrung ({x}, {y})"
SPECTRUM_TRACE_REF = "Referenz"
SPECTRUM_Y_LABEL_RSS = "PSD (g²/Hz)"
SPECTRUM_TRACE_SUM = "Summe X+Y+Z"
SPECTRUM_TRACE_AXIS_TMPL = "PSD {axis}"

HEATMAP_X_LABEL = "x-Bohrung"
HEATMAP_Y_LABEL = "y-Bohrung"

HISTOGRAM_X_LABEL_TMPL = "Beschleunigung ({label})"
HISTOGRAM_Y_LABEL = "Anzahl Löcher"
HISTOGRAM_BINS = "Histogramm-Bins"
HISTOGRAM_EMPTY = "Keine Daten für Histogramm."

WARN_NO_DATA_FOR_HOLE = "{name}: Keine Messdaten für Bohrung ({x}, {y})."

HELP_FOLDER_PLATE = (
    "Ordner mit CSV-Messungen pro Bohrung: Dateinamen im Format "
    "x{N}-y{M}.csv, Spalten: Frequenz_Hz, PSD_X_g2Hz, PSD_Y_g2Hz, "
    "PSD_Z_g2Hz. Optional eine reference.csv für die Referenzmessung."
)
HELP_FREQUENCY_BAND = (
    "Frequenzbereich, über den der Band-RMS integriert wird. "
    "Beeinflusst Heatmap, Spektrum-Hervorhebung und CSV-Export."
)
HELP_AXIS = (
    "X/Y/Z: Einzelachse. RSS = √(gRMS_X² + gRMS_Y² + gRMS_Z²) — "
    "Root Sum of Squares der drei Achsen, nützlich für "
    "richtungsunabhängige Gesamtbelastung."
)
HELP_NORMALIZE = (
    "Teilt jeden Bohrungs-RMS durch den Referenz-RMS derselben Platte. "
    "Ergebnis dimensionslos, Referenz = 1,0. Erfordert reference.csv."
)
HELP_INTERPOLATE = (
    "Wenn deaktiviert, werden nur gemessene Zellen angezeigt; "
    "fehlende Zellen bleiben leer. Standard: aktiv."
)
HELP_HISTOGRAM_BINS = (
    "Anzahl der Bins im Histogramm. Wird automatisch auf die "
    "Anzahl gemessener Löcher reduziert, wenn diese kleiner ist."
)
HELP_SHARED_SCALE = (
    "Wenn aktiv, nutzen alle Heatmaps denselben zmin/zmax-Bereich — "
    "erleichtert den direkten Platten-Vergleich."
)
HELP_COLORSCALE = (
    "Farbpalette der Heatmap. Viridis/Cividis sind perzeptuell "
    "gleichmäßig (empfohlen), RdBu betont Abweichungen."
)
HELP_REF_METRIC = (
    "RMS der Referenzmessung (reference.csv) im aktuellen "
    "Frequenzband. Gelber Stern in der Heatmap markiert diese Stelle."
)
HELP_CSV_EXPORT = (
    "Pro Bohrung eine Zeile: absoluter und normalisierter Band-RMS "
    "für aktuell gewähltes Frequenzband und Achse. UTF-8 mit BOM, "
    "Semikolon-getrennt (Excel-kompatibel)."
)
CAPTION_HEATMAP_LEGEND = (
    "Weiße Kreise = gemessene Bohrungen (anklickbar für Spektrum). "
    "Gelber Stern = Referenzwert in Plattenmitte."
)
