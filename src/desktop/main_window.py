from __future__ import annotations

"""Main application window for the native desktop app.

Holds the :class:`ControlPanel` in the left pane of a horizontal splitter and
reacts to its ``settingsChanged`` signal by re-running the (frontend-agnostic) analysis
pipeline and redrawing — an explicit Qt signal/slot recompute on every
control change.
"""

from PySide6.QtCore import Qt
from PySide6.QtGui import QAction
from PySide6.QtWidgets import (
    QLabel,
    QMainWindow,
    QScrollArea,
    QSplitter,
    QStatusBar,
    QToolBar,
    QVBoxLayout,
    QWidget,
)

from src.core.pipeline import (
    Analysis,
    PlateEntry,
    PlateLoad,
    analyze,
    measured_points,
    ref_marker,
)
from src.core.settings import Settings
from src.desktop.control_panel import ControlPanel
from src.desktop.export import prompt_export
from src.desktop.load_progress import load_with_progress
from src.desktop.manual_dialog import ManualDialog
from src.desktop.plots.heatmap_canvas import HeatmapCanvas
from src.desktop.plots.histogram_canvas import HistogramCanvas
from src.desktop.plots.spectrum_canvas import SpectrumCanvas, SpectrumPoint
from src.core import strings as S

# Settings fields that change the computed result (vs. pure display fields like
# colorscale / histogram_bins). When only display fields change we re-render
# without re-running the expensive load + analyze (scipy interpolation).
_COMPUTE_FIELDS = (
    "folders", "f_min", "f_max", "axis", "normalize", "interpolate",
    "interp_method", "shared_scale",
)


class MainWindow(QMainWindow):
    """Top-level window wiring the control panel to the analysis pipeline."""

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle(S.APP_TITLE)
        self.resize(1280, 860)

        self._control_panel = ControlPanel()

        self._content_scroll = QScrollArea()
        self._content_scroll.setWidgetResizable(True)
        self._content_scroll.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )

        self._main_splitter = QSplitter(Qt.Orientation.Horizontal)
        self._main_splitter.addWidget(self._control_panel)
        self._main_splitter.addWidget(self._content_scroll)
        self._main_splitter.setStretchFactor(0, 0)
        self._main_splitter.setStretchFactor(1, 1)
        self._main_splitter.setSizes([320, 960])
        self.setCentralWidget(self._main_splitter)

        self.setStatusBar(QStatusBar(self))

        toolbar = QToolBar("main", self)
        self.addToolBar(toolbar)
        self._export_action = QAction(S.CSV_EXPORT, self)
        self._export_action.setToolTip(S.HELP_CSV_EXPORT)
        self._export_action.setEnabled(False)
        self._export_action.triggered.connect(self._export)
        toolbar.addAction(self._export_action)

        # Menüleiste mit Hilfe-Menü.
        help_menu = self.menuBar().addMenu(S.MENU_HELP)
        self._manual_action = QAction(S.MENU_HELP_MANUAL, self)
        self._manual_action.triggered.connect(self._show_manual)
        help_menu.addAction(self._manual_action)

        # Latest computed state, kept so other actions (e.g. export) can reuse it.
        self._settings: Settings | None = None
        self._load: PlateLoad | None = None
        self._analysis: Analysis | None = None
        self._is_loading = False
        self._last_good_folder_texts = self._control_panel.folder_texts()

        # Per-plate widgets, rebuilt on every render.
        self._heatmaps: dict[str, HeatmapCanvas] = {}
        self._ref_labels: dict[str, QLabel] = {}
        self._spectrum_canvas: SpectrumCanvas | None = None
        self._spectrum_layout: QVBoxLayout | None = None
        self._selected_points: list[tuple[str, int, int]] = []

        self._set_placeholder(S.WAITING_FOR_FOLDER)
        self._control_panel.settingsChanged.connect(self._refresh)

    # --- pipeline orchestration ---

    def _refresh(self) -> None:
        """Re-run the pipeline for the current settings and update the view.

        Reloading from disk and re-analyzing (scipy interpolation) only happen
        when the relevant settings actually changed; a pure no-op emission or a
        display-only change (e.g. colorscale) skips that expensive work.
        """
        if self._is_loading:
            return
        settings = self._control_panel.current_settings()
        prev = self._settings
        if prev is not None and settings == prev:
            return
        self._settings = settings

        if not settings.folders:
            self._reset_state()
            self._set_placeholder(S.WAITING_FOR_FOLDER)
            self.statusBar().clearMessage()
            return

        folders_changed = prev is None or prev.folders != settings.folders
        load = self._load
        if folders_changed or load is None:
            self._is_loading = True
            try:
                loaded = load_with_progress(self, settings.folders)
            finally:
                self._is_loading = False
            if loaded is None:
                # Option-A cancel: fully revert folder field AND view to the last
                # good state. restore_folder_texts() blocks signals internally, so
                # this revert does not re-trigger _refresh.
                self._control_panel.restore_folder_texts(self._last_good_folder_texts)
                self._settings = prev
                self.statusBar().showMessage(S.LOAD_CANCELLED, 6000)
                return
            self._last_good_folder_texts = self._control_panel.folder_texts()
            self._selected_points = []
            load = loaded
            self._load = load
            self.statusBar().clearMessage()
            for msg in load.errors:
                self.statusBar().showMessage(msg, 10000)

        if not load.plates:
            self._reset_state()
            self._set_placeholder("\n".join(load.errors) or S.WAITING_FOR_FOLDER)
            return

        compute_changed = prev is None or any(
            getattr(prev, f) != getattr(settings, f) for f in _COMPUTE_FIELDS
        )
        analysis = self._analysis
        if compute_changed or analysis is None:
            from PySide6.QtCore import Qt
            from PySide6.QtWidgets import QApplication

            QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
            # Cursor sofort zeichnen, bevor der synchrone analyze()-Aufruf blockiert.
            QApplication.processEvents()
            try:
                analysis = analyze(load.plates, settings)
            finally:
                QApplication.restoreOverrideCursor()
            self._analysis = analysis

        self._export_action.setEnabled(True)
        self._render(settings, load, analysis)

    def _reset_state(self) -> None:
        self._load = None
        self._analysis = None
        self._heatmaps = {}
        self._ref_labels = {}
        self._spectrum_canvas = None
        self._spectrum_layout = None
        self._selected_points = []
        self._export_action.setEnabled(False)

    def _export(self) -> None:
        """Open a save dialog and write the aggregated CSV export."""
        if self._load is None or self._settings is None or not self._load.plates:
            return
        path = prompt_export(
            self,
            self._load.plates,
            f_min=self._settings.f_min,
            f_max=self._settings.f_max,
            axis=self._settings.axis,
        )
        if path:
            self.statusBar().showMessage(f"{S.CSV_EXPORT}: {path}", 8000)

    def _show_manual(self) -> None:
        """Open the modal manual dialog."""
        ManualDialog(self).exec()

    # --- rendering ---

    def _render(self, settings: Settings, load: PlateLoad, analysis: Analysis) -> None:
        """Build the per-plate columns plus the (initially empty) spectrum area."""
        self._heatmaps = {}
        self._ref_labels = {}
        self._spectrum_canvas = None

        plate_splitter = QSplitter(Qt.Orientation.Horizontal)
        for name in load.plates:
            plate_splitter.addWidget(
                self._build_plate_column(name, settings, load.plates[name], analysis)
            )

        spectrum_container = QWidget()
        self._spectrum_layout = QVBoxLayout(spectrum_container)
        hint = QLabel(S.CAPTION_HEATMAP_LEGEND)
        hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        hint.setWordWrap(True)
        self._spectrum_layout.addWidget(hint)

        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.addWidget(plate_splitter)
        content_layout.addWidget(spectrum_container)
        self._content_scroll.setWidget(content)
        if self._selected_points:
            self._draw_spectrum_from_selection()

    def _build_plate_column(
        self,
        name: str,
        settings: Settings,
        entry: PlateEntry,
        analysis: Analysis,
    ) -> QWidget:
        hole_data, _ref_df = entry
        sparse_grid = analysis.grids[name]
        ref_val = analysis.ref_rms.get(name)
        marker = ref_marker(ref_val, normalize=settings.normalize)

        column = QWidget()
        layout = QVBoxLayout(column)

        # Reference metric.
        ref_label = QLabel("")
        if ref_val is not None:
            value_text = (
                S.REF_METRIC_LABEL_NORMALIZED
                if settings.normalize
                else S.REF_METRIC_LABEL_ABS.format(value=ref_val)
            )
            ref_label.setText(
                f"<b>{S.REF_METRIC_HEADER.format(name=name)}</b>: {value_text}"
            )
        self._ref_labels[name] = ref_label
        layout.addWidget(ref_label)

        positions, values = measured_points(sparse_grid, hole_data)

        heatmap = HeatmapCanvas()
        heatmap.render_grid(
            analysis.interp_grids[name],
            plate_name=name,
            title=name,
            colorscale=settings.colorscale,
            normalized=settings.normalize,
            hole_positions=positions,
            hole_values=values,
            ref_value=marker,
            z_range=analysis.z_range,
            selected=self._selected_for_plate(name),
        )
        heatmap.holeClicked.connect(self._on_hole_clicked)
        self._heatmaps[name] = heatmap
        layout.addWidget(heatmap, stretch=3)

        if settings.show_histogram:
            histogram = HistogramCanvas()
            histogram.render_values(
                sparse_grid.ravel(),
                bins=settings.histogram_bins,
                normalized=settings.normalize,
                ref_value=marker,
                x_range=analysis.hist_range if settings.shared_scale else None,
                show_stats=settings.histogram_stats,
            )
            layout.addWidget(histogram, stretch=2)

        return column

    # --- color / selection helpers ---

    @staticmethod
    def _color_for_index(i: int) -> str:
        # matplotlib-Default-Zyklus; koppelt Spektrum-Linie und Heatmap-Marker.
        return f"C{i % 10}"

    def _selected_for_plate(self, name: str) -> list[tuple[int, int, str]]:
        return [
            (x, y, self._color_for_index(i))
            for i, (p, x, y) in enumerate(self._selected_points)
            if p == name
        ]

    def _on_hole_clicked(self, name: str, x_hole: int, y_hole: int) -> None:
        """Update the selected-hole set and redraw spectrum + heatmap markers.

        Plain click replaces the selection; Ctrl/Cmd+click toggles a point
        (Qt maps Cmd to ControlModifier on macOS).
        """
        from PySide6.QtWidgets import QApplication

        if self._load is None or self._settings is None:
            return
        entry = self._load.plates.get(name)
        if entry is None:
            return
        hole_data, _ref_df = entry
        point = (name, x_hole, y_hole)
        additive = bool(
            QApplication.keyboardModifiers() & Qt.KeyboardModifier.ControlModifier
        )

        if additive and point in self._selected_points:
            self._selected_points.remove(point)  # toggle off — no data check needed
        else:
            if (x_hole, y_hole) not in hole_data:
                # Klick auf leere/Gap-Zelle: bestehende Auswahl bewusst NICHT
                # verwerfen (Fehlklick soll eine gute Auswahl nicht zerstören).
                self.statusBar().showMessage(
                    S.WARN_NO_DATA_FOR_HOLE.format(name=name, x=x_hole, y=y_hole), 8000
                )
                return
            if additive:
                self._selected_points.append(point)
            else:
                self._selected_points = [point]

        # Marker auf allen Heatmaps aktualisieren (Farb-Indices verschieben sich
        # beim Entfernen) — inkrementell, ohne den Klick-Sender zu zerstören.
        for plate_name, heatmap in self._heatmaps.items():
            heatmap.set_selected(self._selected_for_plate(plate_name))
        self._draw_spectrum_from_selection()

    def _draw_spectrum_from_selection(self) -> None:
        """Render all selected holes overlaid into one spectrum canvas."""
        if self._spectrum_layout is None or self._load is None or self._settings is None:
            return
        if not self._selected_points:
            self._clear_spectrum()
            return
        points: list[SpectrumPoint] = []
        for i, (name, x, y) in enumerate(self._selected_points):
            entry = self._load.plates.get(name)
            if entry is None:
                continue
            hole_data, ref_df = entry
            if (x, y) not in hole_data:
                continue
            points.append(
                SpectrumPoint(
                    plate_name=name, x_hole=x, y_hole=y,
                    hole_df=hole_data[(x, y)], ref_df=ref_df,
                    color=self._color_for_index(i),
                )
            )
        if not points:
            self._clear_spectrum()
            return
        canvas = SpectrumCanvas()
        canvas.render_spectrum(
            points,
            axis=self._settings.axis,
            f_min=self._settings.f_min,
            f_max=self._settings.f_max,
        )
        self._set_spectrum_canvas(canvas)

    def _clear_spectrum(self) -> None:
        """Drop any spectrum content (e.g. when the selection becomes empty)."""
        if self._spectrum_layout is None:
            return
        while self._spectrum_layout.count():
            item = self._spectrum_layout.takeAt(0)
            if item is None:
                break
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()
        self._spectrum_canvas = None

    def _set_spectrum_canvas(self, canvas: SpectrumCanvas) -> None:
        self._clear_spectrum()
        if self._spectrum_layout is None:
            return
        self._spectrum_layout.addWidget(canvas)
        self._spectrum_canvas = canvas

    def _set_placeholder(self, text: str) -> None:
        placeholder = QLabel(text)
        placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        placeholder.setWordWrap(True)
        self._content_scroll.setWidget(placeholder)

    # --- accessors (used by tests / export) ---

    @property
    def control_panel(self) -> ControlPanel:
        return self._control_panel
