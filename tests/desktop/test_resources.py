from __future__ import annotations

from pathlib import Path

from src.desktop import resources


def test_manual_path_points_to_existing_file():
    path = resources.manual_path()
    assert isinstance(path, Path)
    assert path.name == "ANLEITUNG_DESKTOP.md"
    assert path.exists()


def test_load_manual_text_returns_nonempty():
    text = resources.load_manual_text()
    assert isinstance(text, str)
    assert text.strip()
