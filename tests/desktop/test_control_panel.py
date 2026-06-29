from __future__ import annotations

import pytest

from src.core.settings import Settings
from src.desktop.control_panel import ControlPanel, normalize_path


# --- pure helper -----------------------------------------------------------

@pytest.mark.parametrize("raw,expected", [
    ("  /a/b  ", "/a/b"),
    ('"/a/b"', "/a/b"),
    ("'/a/b'", "/a/b"),
    ("", ""),
])
def test_normalize_path_strips_quotes_and_space(raw, expected):
    assert normalize_path(raw) == expected


# --- widget -> Settings ----------------------------------------------------

def test_current_settings_defaults(qapp):
    panel = ControlPanel()
    s = panel.current_settings()
    assert isinstance(s, Settings)
    assert s.f_min == 0
    assert s.f_max == 25000
    assert s.axis == "X"
    assert s.normalize is False
    assert s.interpolate is True
    assert s.interp_method == "linear"
    assert s.shared_scale is True
    assert s.histogram_bins == 20
    assert s.histogram_stats is True
    assert s.colorscale == "Viridis"
    assert s.folders == ()  # no paths entered yet


def test_current_settings_reflects_histogram_stats_toggle(qapp):
    panel = ControlPanel()
    panel._histogram_stats.setChecked(False)
    assert panel.current_settings().histogram_stats is False


def test_current_settings_includes_entered_folder(qapp):
    panel = ControlPanel()
    panel.set_folder(0, "  /data/plate1  ")
    s = panel.current_settings()
    assert ("Platte 1", "/data/plate1") in s.folders


def test_current_settings_reflects_widget_changes(qapp):
    panel = ControlPanel()
    panel.set_axis("RSS")
    panel.set_frequency_band(100, 5000)
    panel.set_normalize(True)
    s = panel.current_settings()
    assert s.axis == "RSS"
    assert s.f_min == 100
    assert s.f_max == 5000
    assert s.normalize is True


def test_settings_changed_signal_emitted_on_axis_change(qapp):
    panel = ControlPanel()
    received = []
    panel.settingsChanged.connect(lambda: received.append(True))
    panel.set_axis("Y")
    assert received, "settingsChanged should fire when a control changes"


def test_f_min_pushes_f_max_to_keep_strict_order(qapp):
    panel = ControlPanel()
    panel.set_frequency_band(0, 1000)
    panel._f_min.setValue(1000)  # gleich f_max -> muss f_max hochschieben
    s = panel.current_settings()
    assert s.f_max > s.f_min


def test_f_min_at_ceiling_pulls_itself_below_max(qapp):
    panel = ControlPanel()
    panel._f_max.setValue(25000)
    panel._f_min.setValue(25000)  # am Anschlag -> f_min muss unter f_max rutschen
    s = panel.current_settings()
    assert s.f_min < s.f_max
    assert s.f_max == 25000


def test_folder_texts_round_trip(qapp):
    from src.desktop.control_panel import ControlPanel

    panel = ControlPanel()
    panel.set_folder(0, "/a")
    panel.set_folder(1, "/b")
    assert panel.folder_texts() == ["/a", "/b"]


def test_restore_folder_texts_emits_no_signal(qapp):
    from src.desktop.control_panel import ControlPanel

    panel = ControlPanel()
    fired: list[int] = []
    panel.settingsChanged.connect(lambda: fired.append(1))
    panel.restore_folder_texts(["/x", "/y"])
    assert panel.folder_texts() == ["/x", "/y"]
    assert fired == []


def test_frequency_spinboxes_commit_on_enter_not_per_keystroke(qapp):
    panel = ControlPanel()
    # keyboardTracking aus => valueChanged feuert erst bei Enter/Fokusverlust,
    # nicht ab der ersten getippten Ziffer.
    assert panel._f_min.keyboardTracking() is False
    assert panel._f_max.keyboardTracking() is False


def test_show_histogram_default_true(qapp):
    panel = ControlPanel()
    assert panel.current_settings().show_histogram is True


def test_show_histogram_toggle_reflected_in_settings(qapp):
    panel = ControlPanel()
    panel._show_histogram.setChecked(False)
    assert panel.current_settings().show_histogram is False


def test_hiding_histogram_disables_bins_and_stats(qapp):
    panel = ControlPanel()
    panel._show_histogram.setChecked(False)
    assert panel._bins.isEnabled() is False
    assert panel._histogram_stats.isEnabled() is False
    panel._show_histogram.setChecked(True)
    assert panel._bins.isEnabled() is True
    assert panel._histogram_stats.isEnabled() is True
