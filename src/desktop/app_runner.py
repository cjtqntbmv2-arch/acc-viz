from __future__ import annotations

"""Shared bootstrap for the native desktop app, used by both entrypoints.

Centralizes QApplication setup so ``desktop_main.py`` (dev) and
``packaging/entry.py`` (frozen) stay in sync.
"""

import os

from src.logging_setup import get_logger

_LOG = get_logger(__name__)


def build_main_window():
    """Instantiate and return the application's main window (without showing)."""
    from src.desktop.main_window import MainWindow

    return MainWindow()


def run_app(argv: list[str], *, smoke: bool = False) -> int:
    """Create the QApplication, show the main window, run the event loop.

    Args:
        argv: Process argv handed to QApplication.
        smoke: When True, auto-quit shortly after start (for headless smoke tests).
    """
    from PySide6.QtWidgets import QApplication

    app = QApplication.instance() or QApplication(argv)
    window = build_main_window()
    window.show()
    _LOG.info("Desktop app started")

    if smoke or os.environ.get("ACC_VIZ_SMOKE") == "1":
        from PySide6.QtCore import QTimer

        QTimer.singleShot(1500, app.quit)

    return app.exec()
