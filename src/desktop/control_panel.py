from __future__ import annotations

"""Native PySide6 settings panel — the desktop replacement for the Streamlit sidebar.

Mirrors :func:`src.ui.sidebar.render_sidebar`: it exposes the same controls and
produces the same frozen :class:`Settings` snapshot, but as a long-lived widget
that emits :attr:`ControlPanel.settingsChanged` whenever any control changes.
"""

from typing import cast, get_args

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QButtonGroup,
    QCheckBox,
    QComboBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QRadioButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from src.analysis.interpolation import InterpolationMethod
from src.core.colorscales import COLORSCALES
from src.core.settings import Axis, Settings, normalize_path
from src.core import strings as S

# Re-exported for callers/tests that import it from here.
__all__ = ["ControlPanel", "normalize_path"]

# Qt dynamic-property keys backing the radio buttons.
_AXIS_PROP = "axis_value"
_METHOD_PROP = "method_value"
_FREQ_STEP = 100  # Hz; Mindestabstand zwischen f_min und f_max

_FOLDER_DISPLAY_LABELS: tuple[str, str] = (S.FOLDER_PLATE_1, S.FOLDER_PLATE_2)

_INTERP_METHODS: tuple[tuple[str, InterpolationMethod], ...] = (
    (S.INTERP_METHOD_LINEAR, "linear"),
    (S.INTERP_METHOD_TPS, "tps"),
)


class ControlPanel(QWidget):
    """Settings panel emitting :attr:`settingsChanged` on every control change."""

    settingsChanged = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._folder_edits: list[QLineEdit] = []

        root = QVBoxLayout(self)
        root.addWidget(QLabel(f"<b>{S.SIDEBAR_HEADER}</b>"))

        form = QFormLayout()
        form.setRowWrapPolicy(QFormLayout.RowWrapPolicy.WrapAllRows)
        form.setVerticalSpacing(4)
        form.setContentsMargins(0, 0, 0, 0)
        root.addLayout(form)

        # --- folder inputs ---
        for i, display_label in enumerate(_FOLDER_DISPLAY_LABELS):
            row = QHBoxLayout()
            edit = QLineEdit()
            edit.setToolTip(S.HELP_FOLDER_PLATE)
            edit.textChanged.connect(self.settingsChanged)
            browse = QPushButton("📁")
            browse.setToolTip(S.PICK_FOLDER)
            browse.clicked.connect(lambda _=False, idx=i: self._browse(idx))
            row.addWidget(edit)
            row.addWidget(browse)
            self._folder_edits.append(edit)
            container = QWidget()
            container.setLayout(row)
            form.addRow(display_label, container)

        # --- frequency band ---
        self._f_min = QSpinBox()
        self._f_min.setRange(0, 25000)
        self._f_min.setSingleStep(100)
        self._f_min.setValue(0)
        self._f_max = QSpinBox()
        self._f_max.setRange(0, 25000)
        self._f_max.setSingleStep(100)
        self._f_max.setValue(25000)
        self._f_min.valueChanged.connect(self._on_f_min_changed)
        self._f_max.valueChanged.connect(self._on_f_max_changed)
        band = QHBoxLayout()
        band.addWidget(self._f_min)
        band.addWidget(QLabel("–"))
        band.addWidget(self._f_max)
        band_container = QWidget()
        band_container.setLayout(band)
        band_container.setToolTip(S.HELP_FREQUENCY_BAND)
        form.addRow(S.FREQUENCY_BAND, band_container)

        # --- axis ---
        self._axis_group, axis_container = self._radio_group(
            [(ax, ax) for ax in get_args(Axis)],
            prop=_AXIS_PROP,
            default="X",
            tooltip=S.HELP_AXIS,
        )
        form.addRow(S.AXIS, axis_container)

        # --- toggles ---
        self._normalize = QCheckBox(S.NORMALIZE)
        self._normalize.setToolTip(S.HELP_NORMALIZE)
        self._normalize.toggled.connect(self.settingsChanged)
        root.addWidget(self._normalize)

        self._interpolate = QCheckBox(S.INTERPOLATE)
        self._interpolate.setChecked(True)
        self._interpolate.setToolTip(S.HELP_INTERPOLATE)
        self._interpolate.toggled.connect(self._on_interpolate_toggled)
        root.addWidget(self._interpolate)

        # --- interpolation method ---
        self._method_group, self._method_container = self._radio_group(
            list(_INTERP_METHODS),
            prop=_METHOD_PROP,
            default="linear",
            tooltip=S.HELP_INTERP_METHOD,
        )
        form.addRow(S.INTERP_METHOD, self._method_container)

        # --- histogram bins ---
        self._bins = QSpinBox()
        self._bins.setRange(5, 50)
        self._bins.setValue(20)
        self._bins.setToolTip(S.HELP_HISTOGRAM_BINS)
        self._bins.valueChanged.connect(self.settingsChanged)
        form.addRow(S.HISTOGRAM_BINS, self._bins)

        # --- histogram statistics overlay ---
        self._histogram_stats = QCheckBox(S.HISTOGRAM_STATS)
        self._histogram_stats.setChecked(True)
        self._histogram_stats.setToolTip(S.HELP_HISTOGRAM_STATS)
        self._histogram_stats.toggled.connect(self.settingsChanged)
        root.addWidget(self._histogram_stats)

        # --- shared scale ---
        self._shared_scale = QCheckBox(S.SHARED_SCALE)
        self._shared_scale.setChecked(True)
        self._shared_scale.setToolTip(S.HELP_SHARED_SCALE)
        self._shared_scale.toggled.connect(self.settingsChanged)
        root.addWidget(self._shared_scale)

        # --- colorscale ---
        self._colorscale = QComboBox()
        self._colorscale.addItems(COLORSCALES)
        self._colorscale.setToolTip(S.HELP_COLORSCALE)
        self._colorscale.currentTextChanged.connect(self.settingsChanged)
        form.addRow(S.COLORSCALE, self._colorscale)

        root.addStretch(1)

    # --- builders ---

    def _radio_group(
        self,
        items: list[tuple[str, str]],
        *,
        prop: str,
        default: str,
        tooltip: str,
    ) -> tuple[QButtonGroup, QWidget]:
        """Build a horizontal radio-button group backed by a dynamic property.

        Args:
            items: ``(label, value)`` pairs; ``value`` is stored under ``prop``.
            prop: Dynamic-property key holding each button's value.
            default: The value whose button starts checked.
            tooltip: Tooltip for the container.

        Returns:
            The :class:`QButtonGroup` and its container widget.
        """
        group = QButtonGroup(self)
        row = QHBoxLayout()
        for label, value in items:
            btn = QRadioButton(label)
            btn.setProperty(prop, value)
            if value == default:
                btn.setChecked(True)
            group.addButton(btn)
            row.addWidget(btn)
        group.buttonToggled.connect(self._on_radio_toggled)
        container = QWidget()
        container.setLayout(row)
        container.setToolTip(tooltip)
        return group, container

    # --- internal slots ---

    def _on_radio_toggled(self, _btn, checked: bool) -> None:
        # buttonToggled fires for both the unchecked and the newly-checked
        # button; only react to the latter to avoid a redundant emission.
        if checked:
            self.settingsChanged.emit()

    def _browse(self, idx: int) -> None:
        path = QFileDialog.getExistingDirectory(self, S.PICK_FOLDER)
        if path:
            self._folder_edits[idx].setText(path)

    def _on_f_min_changed(self, value: int) -> None:
        # f_max muss strikt größer bleiben. Signale während des Clamps blocken,
        # damit pro Nutzer-Edit genau ein settingsChanged ausgelöst wird.
        if value >= self._f_max.value():
            target = value + _FREQ_STEP
            if target <= self._f_max.maximum():
                self._f_max.blockSignals(True)
                self._f_max.setValue(target)
                self._f_max.blockSignals(False)
            else:
                # f_max am Anschlag: f_min unter f_max ziehen.
                self._f_min.blockSignals(True)
                self._f_min.setValue(self._f_max.value() - _FREQ_STEP)
                self._f_min.blockSignals(False)
        self.settingsChanged.emit()

    def _on_f_max_changed(self, value: int) -> None:
        if value <= self._f_min.value():
            target = value - _FREQ_STEP
            if target >= self._f_min.minimum():
                self._f_min.blockSignals(True)
                self._f_min.setValue(target)
                self._f_min.blockSignals(False)
            else:
                self._f_max.blockSignals(True)
                self._f_max.setValue(self._f_min.value() + _FREQ_STEP)
                self._f_max.blockSignals(False)
        self.settingsChanged.emit()

    def _on_interpolate_toggled(self, checked: bool) -> None:
        self._method_container.setEnabled(checked)
        self.settingsChanged.emit()

    # --- programmatic setters (also used by tests) ---

    def set_folder(self, idx: int, path: str) -> None:
        self._folder_edits[idx].setText(path)

    def set_axis(self, axis: Axis) -> None:
        for btn in self._axis_group.buttons():
            if btn.property(_AXIS_PROP) == axis:
                btn.setChecked(True)
                return

    def set_frequency_band(self, f_min: int, f_max: int) -> None:
        self._f_min.setValue(f_min)
        self._f_max.setValue(f_max)

    def set_normalize(self, value: bool) -> None:
        self._normalize.setChecked(value)

    # --- snapshot ---

    def current_settings(self) -> Settings:
        """Build an immutable :class:`Settings` from the current widget state."""
        folders: list[tuple[str, str]] = []
        for label, edit in zip(S.PLATE_LABELS, self._folder_edits):
            path = normalize_path(edit.text())
            if path:
                folders.append((label, path))

        axis_btn = self._axis_group.checkedButton()
        axis = cast(Axis, axis_btn.property(_AXIS_PROP) if axis_btn else "X")

        method_btn = self._method_group.checkedButton()
        interp_method = cast(
            InterpolationMethod,
            method_btn.property(_METHOD_PROP) if method_btn else "linear",
        )

        return Settings(
            folders=tuple(folders),
            f_min=int(self._f_min.value()),
            f_max=int(self._f_max.value()),
            axis=axis,
            normalize=self._normalize.isChecked(),
            shared_scale=self._shared_scale.isChecked(),
            colorscale=self._colorscale.currentText(),
            interpolate=self._interpolate.isChecked(),
            histogram_bins=int(self._bins.value()),
            histogram_stats=self._histogram_stats.isChecked(),
            interp_method=interp_method,
        )
