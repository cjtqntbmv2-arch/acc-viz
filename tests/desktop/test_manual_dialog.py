from __future__ import annotations

from src.desktop.manual_dialog import ManualDialog
from src.ui import strings as S


def test_dialog_renders_supplied_text(qapp):
    dialog = ManualDialog(text="# Überschrift\n\nEin Absatz.")
    assert dialog.windowTitle() == S.MANUAL_DIALOG_TITLE
    assert "Absatz" in dialog.browser.toPlainText()


def test_dialog_shows_fallback_on_load_error(qapp, monkeypatch):
    from src.desktop import manual_dialog as md

    def boom() -> str:
        raise OSError("missing")

    monkeypatch.setattr(md, "load_manual_text", boom)
    dialog = ManualDialog()
    assert dialog.browser.toPlainText().strip() == S.MANUAL_LOAD_ERROR


def test_dialog_loads_real_manual_by_default(qapp):
    from src.ui import strings as S

    dialog = ManualDialog()
    rendered = dialog.browser.toPlainText()
    assert rendered.strip()
    assert rendered.strip() != S.MANUAL_LOAD_ERROR
