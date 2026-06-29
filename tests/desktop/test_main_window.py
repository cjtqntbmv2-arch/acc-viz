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


# --- multi-select tests (Task 6) ---

def _click(win, name, x, y, *, ctrl=False):
    """Simulate a hole click with optional Ctrl modifier via monkeypatching."""
    from PySide6.QtCore import Qt
    from PySide6.QtWidgets import QApplication

    mods = (
        Qt.KeyboardModifier.ControlModifier if ctrl
        else Qt.KeyboardModifier.NoModifier
    )
    orig = QApplication.keyboardModifiers
    QApplication.keyboardModifiers = staticmethod(lambda: mods)
    try:
        win._on_hole_clicked(name, x, y)
    finally:
        QApplication.keyboardModifiers = orig


def test_plain_click_selects_single_point(qapp, tmp_path):
    from tests.core.conftest import make_plate_folder

    folder = make_plate_folder(tmp_path / "p1", {(0, 0): 1e-3, (1, 1): 4e-3})
    win = MainWindow()
    win.control_panel.set_folder(0, str(folder))
    _click(win, "Platte 1", 0, 0)
    assert win._selected_points == [("Platte 1", 0, 0)]
    _click(win, "Platte 1", 1, 1)  # plain click replaces
    assert win._selected_points == [("Platte 1", 1, 1)]


def test_ctrl_click_accumulates_and_toggles(qapp, tmp_path):
    from tests.core.conftest import make_plate_folder

    folder = make_plate_folder(tmp_path / "p1", {(0, 0): 1e-3, (1, 1): 4e-3})
    win = MainWindow()
    win.control_panel.set_folder(0, str(folder))
    _click(win, "Platte 1", 0, 0)
    _click(win, "Platte 1", 1, 1, ctrl=True)
    assert win._selected_points == [("Platte 1", 0, 0), ("Platte 1", 1, 1)]
    _click(win, "Platte 1", 0, 0, ctrl=True)  # toggle off
    assert win._selected_points == [("Platte 1", 1, 1)]


def test_selection_survives_settings_change(qapp, tmp_path):
    from tests.core.conftest import make_plate_folder

    folder = make_plate_folder(tmp_path / "p1", {(0, 0): 1e-3, (1, 1): 4e-3})
    win = MainWindow()
    win.control_panel.set_folder(0, str(folder))
    _click(win, "Platte 1", 0, 0)
    win.control_panel.set_axis("RSS")  # triggers _refresh -> _render
    assert win._selected_points == [("Platte 1", 0, 0)]
    # Spektrum muss nach dem Re-Render real neu gezeichnet sein (nicht nur != None):
    # RSS + Einzelpunkt, ref_df None => genau eine Summenlinie.
    assert win._spectrum_canvas is not None
    assert len(win._spectrum_canvas.axes.get_lines()) >= 1


def test_folder_change_clears_selection(qapp, tmp_path):
    from tests.core.conftest import make_plate_folder

    folder1 = make_plate_folder(tmp_path / "p1", {(0, 0): 1e-3, (1, 1): 4e-3})
    folder2 = make_plate_folder(tmp_path / "p2", {(0, 0): 2e-3, (1, 1): 5e-3})
    win = MainWindow()
    win.control_panel.set_folder(0, str(folder1))
    _click(win, "Platte 1", 0, 0)
    win.control_panel.set_folder(0, str(folder2))  # new folder -> reload
    assert win._selected_points == []


def test_heatmap_marker_color_matches_spectrum_line(qapp, tmp_path):
    # Pins the color-coupling invariant: each selected point's heatmap ring
    # colour equals its spectrum-line colour (both from the same global index),
    # cross-plate. Holds by construction today; this guards future refactors of
    # _color_for_index / _selected_for_plate.
    import numpy as np
    from matplotlib.colors import to_rgba

    from tests.core.conftest import make_plate_folder

    f1 = make_plate_folder(tmp_path / "p1", {(0, 0): 1e-3, (1, 1): 4e-3})
    f2 = make_plate_folder(tmp_path / "p2", {(0, 0): 2e-3, (1, 1): 5e-3})
    win = MainWindow()
    win.control_panel.set_folder(0, str(f1))
    win.control_panel.set_folder(1, str(f2))
    _click(win, "Platte 1", 0, 0)             # global index 0
    _click(win, "Platte 2", 0, 0, ctrl=True)  # global index 1

    assert win._spectrum_canvas is not None
    lines = win._spectrum_canvas.axes.get_lines()
    assert len(lines) == 2  # one line per point, no ref (multi-selection)
    art1 = win._heatmaps["Platte 1"]._selection_artist
    art2 = win._heatmaps["Platte 2"]._selection_artist
    assert art1 is not None and art2 is not None
    ring1 = np.asarray(art1.get_edgecolor())[0]
    ring2 = np.asarray(art2.get_edgecolor())[0]
    # marker colour == its own spectrum line colour (the coupling), per point
    assert np.allclose(ring1, to_rgba(lines[0].get_color()))
    assert np.allclose(ring2, to_rgba(lines[1].get_color()))
    # and the two points are visually distinct
    assert not np.allclose(ring1, ring2)
