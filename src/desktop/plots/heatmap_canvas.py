from __future__ import annotations

"""Native matplotlib heatmap canvas — the desktop replacement for the Plotly heatmap.

Mirrors :func:`src.ui.heatmap.make_heatmap`: an interpolated grid drawn with the
selected colormap, white markers at measured holes and an optional yellow star at
the plate center for the reference value. Clicking a cell emits
:attr:`HeatmapCanvas.holeClicked` with the snapped integer ``(x, y)`` coordinate,
replacing Streamlit's ``st.plotly_chart(on_select="rerun")``.
"""

import numpy as np
from matplotlib.figure import Figure
from PySide6.QtCore import Signal
from PySide6.QtGui import QCursor
from PySide6.QtWidgets import QToolTip

from src.core.colorscales import to_cmap as colorscale_to_cmap
from src.desktop.plots._canvas_base import ScrollPassthroughCanvas
from src.ui import strings as S

__all__ = ["HeatmapCanvas", "colorscale_to_cmap", "nearest_cell"]

HOLE_MARKER_SIZE = 70
REF_STAR_SIZE = 260

# Floor height (px) so the plot keeps a readable size and the enclosing
# QScrollArea scrolls instead of squeezing the canvas.
_MIN_HEIGHT_PX = 440

_TICK_LABEL_SIZE = 8
# Cap on per-axis ticks so dense plates don't render overlapping labels.
_MAX_AXIS_TICKS = 12
# Colorbar column width (relative to the 1.0 plot column) and the width of an
# empty left column that balances it. The left spacer is wider than the colorbar
# so the plot stays centered even with the colorbar's labels on the right.
_CBAR_WIDTH_RATIO = 0.09
_LEFT_SPACER_RATIO = 0.17


def _axis_ticks(n: int) -> list[int]:
    """Integer tick positions for ``n`` cells, thinned to at most ``_MAX_AXIS_TICKS``."""
    if n <= _MAX_AXIS_TICKS:
        return list(range(n))
    step = -(-n // _MAX_AXIS_TICKS)  # ceil division
    return list(range(0, n, step))


def nearest_cell(
    xdata: float | None,
    ydata: float | None,
    nrows: int,
    ncols: int,
) -> tuple[int, int] | None:
    """Snap click coordinates to the nearest integer grid cell.

    Args:
        xdata: Click x position in data coordinates (hole x), or ``None``.
        ydata: Click y position in data coordinates (hole y), or ``None``.
        nrows: Number of x cells (``grid.shape[0]``).
        ncols: Number of y cells (``grid.shape[1]``).

    Returns:
        The snapped ``(x, y)`` cell, or ``None`` when the click is outside the
        axes or off the grid.
    """
    if xdata is None or ydata is None:
        return None
    x = int(round(xdata))
    y = int(round(ydata))
    if 0 <= x < nrows and 0 <= y < ncols:
        return (x, y)
    return None


def resolve_hover(
    xdata: float | None,
    ydata: float | None,
    *,
    grid: np.ndarray,
    hole_lookup: dict[tuple[int, int], float],
    ref_value: float | None,
    normalized: bool,
) -> str | None:
    """Tooltip text for a cursor data-coordinate over the heatmap, or ``None``.

    Priority: reference star (near center) > measured hole > interpolated cell.
    NaN/gap cells and positions outside the grid return ``None`` (Plotly parity
    with ``hoverongaps=False``).
    """
    if xdata is None or ydata is None:
        return None

    nrows, ncols = grid.shape
    label = S.COLORBAR_NORMALIZED if normalized else S.COLORBAR_ABSOLUTE

    # 1. Reference star at the geometric center takes priority (drawn on top).
    if ref_value is not None:
        cx, cy = (nrows - 1) / 2, (ncols - 1) / 2
        if (xdata - cx) ** 2 + (ydata - cy) ** 2 < 0.25:  # within radius 0.5
            return S.HEATMAP_HOVER_REFERENCE.format(label=label, value=ref_value)

    cell = nearest_cell(xdata, ydata, nrows, ncols)
    if cell is None:
        return None
    x, y = cell

    # 2. Measured hole.
    if (x, y) in hole_lookup:
        return S.HEATMAP_HOVER_MEASURED.format(
            x=x, y=y, label=label, value=hole_lookup[(x, y)]
        )

    # 3. Interpolated cell (skip NaN gaps).
    value = grid[x, y]
    if np.isfinite(value):
        return S.HEATMAP_HOVER_INTERPOLATED.format(
            x=x, y=y, label=label, value=float(value)
        )
    return None


class HeatmapCanvas(ScrollPassthroughCanvas):
    """A clickable matplotlib heatmap for one plate."""

    holeClicked = Signal(str, int, int)  # plate_name, x, y

    def __init__(self) -> None:
        self._figure = Figure(figsize=(5, 5), layout="constrained")
        super().__init__(self._figure)
        self.axes = self._figure.add_subplot(111)
        self.setMinimumHeight(_MIN_HEIGHT_PX)
        self._plate_name = ""
        self._shape = (1, 1)
        self._colorbar = None
        self.mpl_connect("button_press_event", self._on_click)

        self._grid: np.ndarray = np.empty((1, 1))
        self._hole_lookup: dict[tuple[int, int], float] = {}
        self._ref_value: float | None = None
        self._normalized = False
        self._last_hover: str | None = None
        self.mpl_connect("motion_notify_event", self._on_motion)

    def render_grid(
        self,
        grid: np.ndarray,
        *,
        plate_name: str,
        title: str,
        colorscale: str,
        normalized: bool,
        hole_positions: list[tuple[int, int]],
        hole_values: list[float],
        ref_value: float | None,
        z_range: tuple[float, float] | None,
    ) -> None:
        """Draw the interpolated grid with hole markers and optional reference star."""
        self._plate_name = plate_name
        self._shape = (grid.shape[0], grid.shape[1])
        self._grid = grid
        self._hole_lookup = dict(zip(hole_positions, hole_values))
        self._ref_value = ref_value
        self._normalized = normalized
        nrows, ncols = grid.shape

        self._figure.clear()
        # Empty left column (same width as the colorbar column) balances the
        # colorbar so the square plot is centered in the canvas.
        gs = self._figure.add_gridspec(
            1, 3, width_ratios=[_LEFT_SPACER_RATIO, 1.0, _CBAR_WIDTH_RATIO]
        )
        self.axes = self._figure.add_subplot(gs[0, 1])
        cax = self._figure.add_subplot(gs[0, 2])
        self._colorbar = None

        label = S.COLORBAR_NORMALIZED if normalized else S.COLORBAR_ABSOLUTE
        vmin, vmax = (z_range if z_range else (None, None))

        # grid[x, y] -> display M[y, x] so the x-axis is hole x and y-axis hole y.
        # origin="upper" puts y=0 at the top, matching the Plotly reversed y-axis.
        masked = np.ma.masked_invalid(grid.T)
        cmap = colorscale_to_cmap(colorscale)
        im = self.axes.imshow(
            masked,
            origin="upper",
            cmap=cmap,
            vmin=vmin,
            vmax=vmax,
            aspect="equal",
            interpolation="nearest",
        )
        self._colorbar = self._figure.colorbar(im, cax=cax, label=label)

        if hole_positions:
            xs = [x for (x, _) in hole_positions]
            ys = [y for (_, y) in hole_positions]
            self.axes.scatter(
                xs, ys,
                s=HOLE_MARKER_SIZE,
                facecolors=(1, 1, 1, 0.4),
                edgecolors=(0, 0, 0, 0.7),
                linewidths=1.5,
                zorder=3,
            )

        if ref_value is not None:
            self.axes.scatter(
                [(nrows - 1) / 2], [(ncols - 1) / 2],
                s=REF_STAR_SIZE,
                marker="*",
                facecolors=(1, 1, 0, 0.9),
                edgecolors="black",
                linewidths=1.5,
                zorder=4,
            )

        self.axes.set_title(title)
        self.axes.set_xlabel(S.HEATMAP_X_LABEL)
        self.axes.set_ylabel(S.HEATMAP_Y_LABEL)
        self.axes.set_xticks(_axis_ticks(nrows))
        self.axes.set_yticks(_axis_ticks(ncols))
        self.axes.tick_params(labelsize=_TICK_LABEL_SIZE)
        self.draw_idle()

    def _on_click(self, event) -> None:
        if getattr(event, "inaxes", None) is not self.axes:
            return
        cell = nearest_cell(
            getattr(event, "xdata", None),
            getattr(event, "ydata", None),
            self._shape[0],
            self._shape[1],
        )
        if cell is not None:
            self.holeClicked.emit(self._plate_name, cell[0], cell[1])

    def _on_motion(self, event) -> None:
        if getattr(event, "inaxes", None) is not self.axes:
            if self._last_hover is not None:
                QToolTip.hideText()
                self._last_hover = None
            return
        text = resolve_hover(
            getattr(event, "xdata", None),
            getattr(event, "ydata", None),
            grid=self._grid,
            hole_lookup=self._hole_lookup,
            ref_value=self._ref_value,
            normalized=self._normalized,
        )
        if text == self._last_hover:
            return
        self._last_hover = text
        if text:
            QToolTip.showText(QCursor.pos(), text, self)
        else:
            QToolTip.hideText()
