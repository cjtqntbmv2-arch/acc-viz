from __future__ import annotations

"""Entry point for the native PySide6 desktop application.

Run with ``python desktop_main.py``. This replaces the Streamlit web app
(``app.py``) for the packaged, native desktop build.
"""

import sys

from src.logging_setup import get_logger

_LOG = get_logger(__name__)


def main() -> int:
    from PySide6.QtWidgets import QApplication

    from src.desktop.main_window import MainWindow

    app = QApplication.instance() or QApplication(sys.argv)
    window = MainWindow()
    window.show()
    _LOG.info("Desktop app started")
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
