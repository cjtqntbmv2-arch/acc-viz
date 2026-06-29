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
    from src.core import strings as S

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
    assert created["parent"] is win


def test_refresh_cancel_reverts_field_and_keeps_state(qapp, tmp_path, monkeypatch):
    from src.desktop import main_window as mw
    from src.core import strings as S
    from tests.core.conftest import make_plate_folder

    folder = make_plate_folder(tmp_path / "p1", {(0, 0): 1e-3, (1, 1): 4e-3})
    win = MainWindow()
    win.control_panel.set_folder(0, str(folder))     # successful load + analyze
    assert win._analysis is not None
    prior_analysis = win._analysis
    prior_load = win._load
    good_texts = win.control_panel.folder_texts()

    # Next reload is cancelled.
    monkeypatch.setattr(mw, "load_with_progress", lambda *a, **k: None)
    folder2 = make_plate_folder(tmp_path / "p2", {(0, 0): 2e-3, (1, 1): 5e-3})
    win.control_panel.set_folder(1, str(folder2))    # folders change -> reload -> cancel

    assert win._analysis is prior_analysis            # view untouched
    assert win._load is prior_load
    assert win.control_panel.folder_texts() == good_texts   # field reverted (Option A)
    assert S.LOAD_CANCELLED in win.statusBar().currentMessage()


def test_refresh_cancel_then_repick_reloads(qapp, tmp_path, monkeypatch):
    from src.desktop import main_window as mw
    from tests.core.conftest import make_plate_folder

    f1 = make_plate_folder(tmp_path / "p1", {(0, 0): 1e-3, (1, 1): 4e-3})
    win = MainWindow()
    win.control_panel.set_folder(0, str(f1))          # initial successful load
    assert win._analysis is not None
    first_analysis = win._analysis

    real_load = mw.load_with_progress                 # capture before patching

    # Cancel a reload to a second folder; field + view must revert.
    monkeypatch.setattr(mw, "load_with_progress", lambda *a, **k: None)
    f2 = make_plate_folder(tmp_path / "p2", {(0, 0): 9e-3, (1, 1): 9e-3})
    win.control_panel.set_folder(1, str(f2))          # reload -> cancelled
    assert win.control_panel.folder_texts() == [str(f1), ""]
    assert win._analysis is first_analysis

    # Restore the real loader and re-pick the SAME folder2: it must now load.
    monkeypatch.setattr(mw, "load_with_progress", real_load)
    win.control_panel.set_folder(1, str(f2))
    assert win._analysis is not first_analysis
    assert "Platte 2" in win._analysis.grids


def test_histogram_hidden_when_show_histogram_false(qapp, tmp_path):
    from src.desktop.plots.histogram_canvas import HistogramCanvas
    from tests.core.conftest import make_plate_folder

    folder = make_plate_folder(tmp_path / "p1", {(0, 0): 1e-3, (1, 1): 4e-3})
    win = MainWindow()
    win.control_panel._show_histogram.setChecked(False)  # triggers settingsChanged
    win.control_panel.set_folder(0, str(folder))          # triggers _refresh + render
    content = win._content_scroll.widget()
    assert content is not None  # widget() is QWidget | None
    histograms = content.findChildren(HistogramCanvas)
    assert histograms == []


def test_histogram_shown_by_default(qapp, tmp_path):
    from src.desktop.plots.histogram_canvas import HistogramCanvas
    from tests.core.conftest import make_plate_folder

    folder = make_plate_folder(tmp_path / "p1", {(0, 0): 1e-3, (1, 1): 4e-3})
    win = MainWindow()
    win.control_panel.set_folder(0, str(folder))
    content = win._content_scroll.widget()
    assert content is not None  # widget() is QWidget | None
    assert len(content.findChildren(HistogramCanvas)) >= 1
