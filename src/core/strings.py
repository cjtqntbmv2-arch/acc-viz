from __future__ import annotations

PAGE_TITLE = "Beschleunigungs-Visualisierung"
APP_TITLE = "Beschleunigungs-Visualisierung — Plattenanalyse"

SIDEBAR_HEADER = "Einstellungen"
# Plate identifiers used as keys/labels throughout (Settings.folders, plate names).
PLATE_LABELS = ("Platte 1", "Platte 2")
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
ANALYZING = "Analyse läuft …"
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
SPECTRUM_TITLE_MULTI = "Spektrum · Achse {axis} · {n} Bohrungen"
SPECTRUM_X_LABEL = "Frequenz (Hz)"
SPECTRUM_Y_LABEL_TMPL = "PSD {axis} (g²/Hz)"
SPECTRUM_TRACE_POINT_TMPL = "{plate} — ({x}, {y})"
SPECTRUM_TRACE_REF = "Referenz"
SPECTRUM_Y_LABEL_RSS = "PSD (g²/Hz)"

HEATMAP_X_LABEL = "x-Bohrung"
HEATMAP_Y_LABEL = "y-Bohrung"

HEATMAP_HOVER_MEASURED = "x={x}, y={y}\n{label}={value:.4f}"
HEATMAP_HOVER_INTERPOLATED = "x={x}, y={y}\nInterpoliert ({label})={value:.4f}"
HEATMAP_HOVER_REFERENCE = "Referenz (Mitte)\n{label}={value:.4f}"

HISTOGRAM_X_LABEL_TMPL = "Beschleunigung ({label})"
HISTOGRAM_Y_LABEL = "Anzahl Löcher"
HISTOGRAM_BINS = "Histogramm-Bins"
HISTOGRAM_EMPTY = "Keine Daten für Histogramm."
HEATMAP_EMPTY = "Keine Messwerte im gewählten Frequenzband."
HISTOGRAM_STATS = "Statistik anzeigen"
SHOW_HISTOGRAM = "Histogramm anzeigen"
HISTOGRAM_STAT_MEAN = "µ = {value:.3g}"
HISTOGRAM_STAT_MEDIAN = "Median = {value:.3g}"
HISTOGRAM_STAT_SIGMA = "±1σ ({value:.3g})"

WARN_NO_DATA_FOR_HOLE = "{name}: Keine Messdaten für Bohrung ({x}, {y})."

HELP_FOLDER_PLATE = (
    "Ordner mit CSV-Messungen pro Bohrung: Dateinamen im Format "
    "x{N}-y{M}.csv, Spalten: Frequenz_Hz, PSD_X_g2Hz, PSD_Y_g2Hz, "
    "PSD_Z_g2Hz. Optional eine Referenz.csv für die Referenzmessung."
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
    "Ergebnis dimensionslos, Referenz = 1,0. Erfordert Referenz.csv."
)
HELP_INTERPOLATE = (
    "Wenn deaktiviert, werden nur gemessene Zellen angezeigt; "
    "fehlende Zellen bleiben leer. Standard: aktiv."
)

# Interpolations-Methode
INTERP_METHOD = "Interpolations-Methode"
INTERP_METHOD_LINEAR = "Linear (Delaunay)"
INTERP_METHOD_TPS = "Thin-Plate-Spline"
HELP_INTERP_METHOD = (
    "Linear: schnell, zeigt Dreiecks-Facetten und bricht bei kollinearen Messpunkten ab. "
    "Thin-Plate-Spline: glatte, physikalisch plausible Fläche, robust bei wenigen oder "
    "kollinearen Punkten."
)

HELP_HISTOGRAM_BINS = (
    "Anzahl der Bins im Histogramm. Wird automatisch auf die "
    "Anzahl gemessener Löcher reduziert, wenn diese kleiner ist."
)
HELP_SHARED_SCALE = (
    "Wenn aktiv, nutzen alle Heatmaps denselben zmin/zmax-Bereich — "
    "erleichtert den direkten Platten-Vergleich."
)
HELP_HISTOGRAM_STATS = (
    "Blendet Mittelwert, Median und ±1σ als vertikale Linien mit "
    "Zahlenwerten im Histogramm ein."
)
HELP_SHOW_HISTOGRAM = (
    "Blendet das Histogramm unter jeder Heatmap ein oder aus. "
    "Reine Anzeige — ändert die Berechnung nicht."
)
HELP_COLORSCALE = (
    "Farbpalette der Heatmap. Viridis/Cividis sind perzeptuell "
    "gleichmäßig (empfohlen), RdBu betont Abweichungen."
)
HELP_REF_METRIC = (
    "RMS der Referenzmessung (Referenz.csv) im aktuellen "
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

# --- Hilfe-Menü / Anleitungs-Dialog ---
MENU_HELP = "Hilfe"
MENU_HELP_MANUAL = "Anleitung"
MANUAL_DIALOG_TITLE = "Anleitung — Beschleunigungs-Visualisierung"
MANUAL_LOAD_ERROR = "Anleitung konnte nicht geladen werden."

# --- Lade-Fortschritt -------------------------------------------------------
LOAD_PROGRESS_TITLE = "Lade Messdateien…"
LOAD_PROGRESS_LABEL = "Datei {i} von {n}"
LOAD_CANCEL = "Abbrechen"
LOAD_CANCELLED = "Laden abgebrochen"
