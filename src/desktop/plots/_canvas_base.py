from __future__ import annotations

"""Shared base for the desktop matplotlib canvases.

:class:`FigureCanvasQTAgg` accepts wheel events (it emits its own matplotlib
``scroll_event``), which stops an enclosing :class:`QScrollArea` from scrolling
while the cursor sits over a plot. None of these canvases use matplotlib scroll
interactions, so we forward the wheel event to the enclosing scroll area's
viewport instead (and ignore it if there is no scroll area).
"""

from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from PySide6.QtGui import QWheelEvent
from PySide6.QtWidgets import QAbstractScrollArea, QApplication


class ScrollPassthroughCanvas(FigureCanvasQTAgg):
    """Matplotlib canvas that forwards wheel events to an enclosing scroll area."""

    def wheelEvent(self, event: QWheelEvent) -> None:  # noqa: N802 (Qt camelCase)
        widget = self.parentWidget()
        while widget is not None:
            if isinstance(widget, QAbstractScrollArea):
                QApplication.sendEvent(widget.viewport(), event)
                return
            widget = widget.parentWidget()
        event.ignore()
