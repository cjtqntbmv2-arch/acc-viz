from __future__ import annotations


def test_build_main_window_returns_window(qapp):
    from src.desktop.app_runner import build_main_window

    window = build_main_window()
    assert window is not None
    assert window.windowTitle()  # nicht-leerer Titel
