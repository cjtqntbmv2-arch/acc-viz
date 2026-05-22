from __future__ import annotations

"""Native matplotlib heatmap canvas — the desktop replacement for the Plotly heatmap.

Mirrors :func:`src.ui.heatmap.make_heatmap`: an interpolated grid drawn with the
selected colormap, white markers at measured holes and an optional yellow star at
the plate center for the reference value. Clicking a cell emits
:attr:`HeatmapCanvas.holeClicked` with the snapped integer ``(x, y)`` coordinate,
replacing Streamlit's ``st.plotly_chart(on_select="rerun")``.
"""

import numpy as np
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.figure import Figure
from PySide6.QtCore import Signal

from src.core.colorscales import to_cmap as colorscale_to_cmap
from src.ui import strings as S

__all__ = ["HeatmapCanvas", "colorscale_to_cmap", "nearest_cell"]

HOLE_MARKER_SIZE = 70
REF_STAR_SIZE = 260


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


class HeatmapCanvas(FigureCanvasQTAgg):
    """A clickable matplotlib heatmap for one plate."""

    holeClicked = Signal(str, int, int)  # plate_name, x, y

    def __init__(self) -> None:
        self._figure = Figure(figsize=(5, 5), layout="constrained")
        super().__init__(self._figure)
        self.axes = self._figure.add_subplot(111)
        self._plate_name = ""
        self._shape = (1, 1)
        self._colorbar = None
        self.mpl_connect("button_press_event", self._on_click)

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
        nrows, ncols = grid.shape

        self._figure.clear()
        self.axes = self._figure.add_subplot(111)
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
        self._colorbar = self._figure.colorbar(im, ax=self.axes, label=label)

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
        self.axes.set_xticks(range(nrows))
        self.axes.set_yticks(range(ncols))
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
