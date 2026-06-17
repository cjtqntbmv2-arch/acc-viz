from __future__ import annotations

"""Entry point for the native PySide6 desktop application.

Run with ``python desktop_main.py``. This is the entry point for the
packaged, native desktop build.
"""

import sys

from src.desktop.app_runner import run_app


def main() -> int:
    return run_app(sys.argv)


if __name__ == "__main__":
    raise SystemExit(main())
