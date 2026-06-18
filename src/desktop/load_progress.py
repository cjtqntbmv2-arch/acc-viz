from __future__ import annotations

"""Cooperative modal progress dialog for loading plate folders on the UI thread.

Owns every Qt specific of the loading UX (dialog lifecycle, ``processEvents``,
cancellation) so that :mod:`src.core.pipeline` and :mod:`src.io` stay Qt-free.
"""

from collections.abc import Callable, Sequence

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QProgressDialog, QWidget

from src.core import strings as S
from src.core.pipeline import PlateLoad, load_plates
from src.io.schema import LoadCancelled


def load_with_progress(
    parent: QWidget | None,
    folders: Sequence[tuple[str, str]],
    *,
    dialog_factory: Callable[[], QProgressDialog] | None = None,
) -> PlateLoad | None:
    """Load ``folders`` while driving a modal progress dialog.

    Returns the :class:`PlateLoad`, or ``None`` if the user cancelled. The dialog
    is built lazily on the first progress tick, so cache hits / small folders
    create no widget and never flicker.
    """
    def _default_factory() -> QProgressDialog:
        return QProgressDialog(S.LOAD_PROGRESS_TITLE, S.LOAD_CANCEL, 0, 0, parent)

    factory = dialog_factory or _default_factory
    holder: dict[str, QProgressDialog] = {}

    def on_progress(done: int, total: int, name: str) -> None:
        dlg = holder.get("dlg")
        if dlg is None:
            dlg = factory()
            dlg.setWindowModality(Qt.WindowModality.ApplicationModal)
            dlg.setMinimumDuration(400)
            dlg.setAutoClose(False)
            dlg.setAutoReset(False)
            dlg.setRange(0, total)
            holder["dlg"] = dlg
        dlg.setValue(done)
        dlg.setLabelText(S.LOAD_PROGRESS_LABEL.format(i=done, n=total))
        QApplication.processEvents()
        if dlg.wasCanceled():
            raise LoadCancelled

    try:
        return load_plates(folders, progress=on_progress)
    except LoadCancelled:
        return None
    finally:
        dlg = holder.get("dlg")
        if dlg is not None:
            dlg.close()
