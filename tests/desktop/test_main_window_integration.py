from __future__ import annotations

from src.desktop.main_window import MainWindow
from tests.core.conftest import make_plate_folder


def test_two_plates_build_two_heatmaps(qapp, tmp_path):
    f1 = make_plate_folder(tmp_path / "p1", {(0, 0): 1e-3, (1, 1): 4e-3})
    f2 = make_plate_folder(tmp_path / "p2", {(0, 0): 2e-3, (1, 1): 5e-3})
    win = MainWindow()
    win.control_panel.set_folder(0, str(f1))
    win.control_panel.set_folder(1, str(f2))
    assert set(win._heatmaps.keys()) == {"Platte 1", "Platte 2"}


def test_clicking_valid_hole_renders_spectrum(qapp, tmp_path):
    folder = make_plate_folder(tmp_path / "p1", {(0, 0): 1e-3, (1, 1): 4e-3})
    win = MainWindow()
    win.control_panel.set_folder(0, str(folder))
    win._on_hole_clicked("Platte 1", 0, 0)
    assert win._spectrum_canvas is not None


def test_clicking_empty_hole_renders_no_spectrum(qapp, tmp_path):
    # Diagonal holes -> cell (0, 1) has no measurement.
    folder = make_plate_folder(tmp_path / "p1", {(0, 0): 1e-3, (1, 1): 4e-3})
    win = MainWindow()
    win.control_panel.set_folder(0, str(folder))
    win._on_hole_clicked("Platte 1", 0, 1)
    assert win._spectrum_canvas is None


def test_display_only_change_skips_reanalyze(qapp, tmp_path, monkeypatch):
    import src.desktop.main_window as mw

    folder = make_plate_folder(tmp_path / "p1", {(0, 0): 1e-3, (1, 1): 4e-3})
    win = MainWindow()
    win.control_panel.set_folder(0, str(folder))  # initial load + analyze

    calls = {"n": 0}
    real_analyze = mw.analyze

    def counting_analyze(*a, **k):
        calls["n"] += 1
        return real_analyze(*a, **k)

    monkeypatch.setattr(mw, "analyze", counting_analyze)

    # Display-only change: colorscale must NOT re-run analyze (scipy work).
    win.control_panel._colorscale.setCurrentText("Plasma")
    assert calls["n"] == 0

    # Compute-relevant change: axis MUST re-run analyze.
    win.control_panel.set_axis("Y")
    assert calls["n"] == 1


def test_export_action_enabled_after_load(qapp, tmp_path):
    folder = make_plate_folder(tmp_path / "p1", {(0, 0): 1e-3, (1, 1): 4e-3})
    win = MainWindow()
    assert win._export_action.isEnabled() is False
    win.control_panel.set_folder(0, str(folder))
    assert win._export_action.isEnabled() is True


def test_reference_metric_shown_when_reference_present(qapp, tmp_path):
    folder = make_plate_folder(tmp_path / "p1", {(0, 0): 4e-3}, ref_val=1e-3)
    win = MainWindow()
    win.control_panel.set_folder(0, str(folder))
    assert "Platte 1" in win._ref_labels
    assert win._ref_labels["Platte 1"].text() != ""
