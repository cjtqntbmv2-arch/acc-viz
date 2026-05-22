from __future__ import annotations

"""Shared fixtures for the PySide6 desktop tests.

Forces the Qt 'offscreen' platform so the tests run headless in CI and locally
without opening real windows.
"""

import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


@pytest.fixture(scope="session")
def qapp():
    from PySide6.QtWidgets import QApplication

    app = QApplication.instance() or QApplication([])
    yield app
