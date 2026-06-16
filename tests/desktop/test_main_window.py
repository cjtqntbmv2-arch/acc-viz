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


def test_refresh_resets_override_cursor(qapp, tmp_path):
    from PySide6.QtWidgets import QApplication

    from src.desktop.main_window import MainWindow
    from tests.core.conftest import make_plate_folder

    folder = make_plate_folder(tmp_path / "p1", {(0, 0): 1e-3, (1, 1): 4e-3})
    win = MainWindow()
    win.control_panel.set_folder(0, str(folder))
    # Nach dem (synchronen) Refresh darf kein Override-Cursor hängen bleiben.
    assert QApplication.overrideCursor() is None


def test_help_menu_has_manual_action(qapp):
    from src.ui import strings as S

    win = MainWindow()
    menu_titles = [a.text() for a in win.menuBar().actions()]
    assert S.MENU_HELP in menu_titles
    assert win._manual_action.text() == S.MENU_HELP_MANUAL


def test_show_manual_opens_dialog(qapp, monkeypatch):
    from src.desktop import main_window as mw

    created = {}

    class FakeDialog:
        def __init__(self, parent):
            created["parent"] = parent

        def exec(self):
            created["exec"] = True
            return 0

    monkeypatch.setattr(mw, "ManualDialog", FakeDialog)
    win = MainWindow()
    win._manual_action.trigger()
    assert created.get("exec") is True
