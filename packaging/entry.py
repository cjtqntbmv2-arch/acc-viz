from __future__ import annotations

"""Frozen-app entry point: launch the native PySide6 desktop application.

Replaces the former Streamlit bootstrap. When ``ACC_VIZ_SMOKE=1`` the app quits
itself after a short delay so the packaging smoke test can assert a clean exit
without a human closing the window.
"""

import logging
import os
import sys
from pathlib import Path


def main() -> int:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    # When frozen, PyInstaller unpacks to sys._MEIPASS; otherwise use repo root.
    base = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent.parent))
    os.chdir(base)
    if str(base) not in sys.path:
        sys.path.insert(0, str(base))

    from PySide6.QtWidgets import QApplication

    from src.desktop.main_window import MainWindow

    app = QApplication.instance() or QApplication(sys.argv)
    window = MainWindow()
    window.show()

    if os.environ.get("ACC_VIZ_SMOKE") == "1":
        from PySide6.QtCore import QTimer

        QTimer.singleShot(1500, app.quit)

    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
