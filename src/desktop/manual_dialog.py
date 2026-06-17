from __future__ import annotations

"""Modal dialog rendering the application manual from Markdown.

Reads the canonical manual via :func:`src.desktop.resources.load_manual_text`
and renders it with ``QTextBrowser.setMarkdown``. On read failure it shows a
plain fallback message instead of crashing.
"""

from typing import TYPE_CHECKING

from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QTextBrowser,
    QVBoxLayout,
)

if TYPE_CHECKING:
    from PySide6.QtWidgets import QWidget

from src.desktop.resources import load_manual_text
from src.core import strings as S


class ManualDialog(QDialog):
    """Scrollable, modal manual viewer."""

    def __init__(self, parent: QWidget | None = None, *, text: str | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle(S.MANUAL_DIALOG_TITLE)
        self.resize(760, 620)

        layout = QVBoxLayout(self)

        self.browser = QTextBrowser(self)
        self.browser.setOpenExternalLinks(True)
        layout.addWidget(self.browser)

        if text is None:
            try:
                text = load_manual_text()
            except OSError:
                text = None

        if text is None:
            self.browser.setPlainText(S.MANUAL_LOAD_ERROR)
        else:
            self.browser.setMarkdown(text)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close, self)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
