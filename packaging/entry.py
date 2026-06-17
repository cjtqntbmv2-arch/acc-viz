from __future__ import annotations

"""Frozen-app entry point: launch the native PySide6 desktop application.

When ``ACC_VIZ_SMOKE=1`` the app quits
itself after a short delay so the packaging smoke test can assert a clean exit
without a human closing the window.
"""

import os
import sys
from pathlib import Path


def main() -> int:
    # When frozen, PyInstaller unpacks to sys._MEIPASS; otherwise use repo root.
    base = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent.parent))
    os.chdir(base)
    if str(base) not in sys.path:
        sys.path.insert(0, str(base))

    from src.desktop.app_runner import run_app

    return run_app(sys.argv)


if __name__ == "__main__":
    raise SystemExit(main())
