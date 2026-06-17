![version](https://img.shields.io/badge/version-0.5.0-blue)

# acc_visualisation

Auswertung und Visualisierung von Beschleunigungs-PSD-Messungen an
Plattenbohrungen: Band-RMS-Heatmaps pro Platte, PSD-Spektrum-Drilldown,
optionale Normalisierung und Interpolation, CSV-Export.

Details zu Input-Format, Funktionsweise und Output: [BESCHREIBUNG.md](BESCHREIBUNG.md)
Kurzbeschreibung und Anleitung der Desktop-App: [ANLEITUNG_DESKTOP.md](ANLEITUNG_DESKTOP.md)

## Start

**Desktop-App (PySide6, nativ):**

```bash
python3 desktop_main.py
```

## Entwicklung

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python -m pytest
```

Packaging zur nativen `.app`/`.exe` via PyInstaller: siehe [packaging/](packaging/).
