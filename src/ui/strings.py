from __future__ import annotations

PAGE_TITLE = "Beschleunigungsverteilung"
APP_TITLE = "Beschleunigungsverteilung — Plattenanalyse"

SIDEBAR_HEADER = "Einstellungen"
FOLDER_PLATE_1 = "Platte 1 — Ordnerpfad"
FOLDER_PLATE_2 = "Platte 2 — Ordnerpfad (optional)"
PICK_FOLDER = "Ordner wählen"

FREQUENCY_BAND = "Frequenzband (Hz)"
AXIS = "Achse"
NORMALIZE = "Normalisiert (relativ zur Referenz)"
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

HEATMAP_X_LABEL = "x-Bohrung"
HEATMAP_Y_LABEL = "y-Bohrung"

WARN_NO_DATA_FOR_HOLE = "{name}: Keine Messdaten für Bohrung ({x}, {y})."
