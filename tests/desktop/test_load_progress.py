from __future__ import annotations

from typing import cast

from PySide6.QtWidgets import QProgressDialog

from src.desktop.load_progress import load_with_progress


class FakeDialog:
    """Minimal stand-in for QProgressDialog recording the helper's calls."""

    def __init__(self, cancel_after: int | None = None) -> None:
        self.values: list[int] = []
        self.labels: list[str] = []
        self.range: tuple[int, int] | None = None
        self.closed = False
        self._cancel_after = cancel_after

    def setWindowModality(self, *_): pass
    def setMinimumDuration(self, *_): pass
    def setAutoClose(self, *_): pass
    def setAutoReset(self, *_): pass
    def setRange(self, lo, hi): self.range = (lo, hi)
    def setLabelText(self, text): self.labels.append(text)
    def setValue(self, value): self.values.append(value)
    def close(self): self.closed = True

    def wasCanceled(self) -> bool:
        return self._cancel_after is not None and len(self.values) >= self._cancel_after


def test_load_with_progress_drives_dialog_and_returns_load(qapp, tmp_path):
    from tests.core.conftest import make_plate_folder

    folder = make_plate_folder(tmp_path / "p1", {(0, 0): 1e-3, (1, 1): 4e-3})
    fake = FakeDialog()
    load = load_with_progress(
        None, [("Platte 1", str(folder))], dialog_factory=lambda: cast(QProgressDialog, fake)
    )
    assert load is not None
    assert "Platte 1" in load.plates
    assert fake.range == (0, 2)
    assert fake.values == [1, 2]
    assert fake.closed is True


def test_load_with_progress_no_files_creates_no_dialog(qapp, tmp_path):
    from tests.core.conftest import make_plate_folder
    from src.core.pipeline import load_plates

    folder = make_plate_folder(tmp_path / "p1", {(0, 0): 1e-3, (1, 1): 4e-3})
    load_plates([("Platte 1", str(folder))])           # warm cache
    created = {"n": 0}

    def factory() -> QProgressDialog:
        created["n"] += 1
        return cast(QProgressDialog, FakeDialog())

    load = load_with_progress(None, [("Platte 1", str(folder))], dialog_factory=factory)
    assert load is not None
    assert created["n"] == 0


def test_load_with_progress_cancel_returns_none(qapp, tmp_path):
    from tests.core.conftest import make_plate_folder

    folder = make_plate_folder(tmp_path / "p1", {(0, 0): 1e-3, (1, 1): 4e-3})
    fake = FakeDialog(cancel_after=1)
    load = load_with_progress(
        None, [("Platte 1", str(folder))], dialog_factory=lambda: cast(QProgressDialog, fake)
    )
    assert load is None
    assert fake.closed is True
