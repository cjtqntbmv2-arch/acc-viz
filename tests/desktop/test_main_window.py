from __future__ import annotations

from src.desktop.main_window import MainWindow


def test_main_window_constructs(qapp):
    win = MainWindow()
    assert win.windowTitle()
    assert win.control_panel is not None


def test_refresh_with_no_folders_keeps_placeholder(qapp):
    win = MainWindow()
    win.control_panel.set_axis("Y")  # triggers settingsChanged -> _refresh
    assert win._analysis is None


def test_refresh_loads_and_analyzes_real_plate(qapp, tmp_path):
    from tests.core.conftest import make_plate_folder

    folder = make_plate_folder(tmp_path / "p1", {(0, 0): 1e-3, (1, 1): 4e-3})
    win = MainWindow()
    win.control_panel.set_folder(0, str(folder))  # triggers _refresh
    assert win._analysis is not None
    assert "Platte 1" in win._analysis.grids
