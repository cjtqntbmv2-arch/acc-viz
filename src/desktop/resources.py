from __future__ import annotations

"""Resource resolution for bundled data files (dev vs. PyInstaller frozen).

The manual lives as a single canonical Markdown file at the project root in dev
and is copied to the bundle root by the PyInstaller spec, where ``sys._MEIPASS``
points at the bundle directory.
"""

import sys
from pathlib import Path

_MANUAL_FILENAME = "ANLEITUNG_DESKTOP.md"


def _base_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(getattr(sys, "_MEIPASS"))
    # src/desktop/resources.py -> project root is parents[2].
    return Path(__file__).resolve().parents[2]


def manual_path() -> Path:
    """Absolute path to the canonical manual Markdown file."""
    return _base_dir() / _MANUAL_FILENAME


def load_manual_text() -> str:
    """Read the manual Markdown as UTF-8 text."""
    return manual_path().read_text(encoding="utf-8")
