from __future__ import annotations

"""Native matplotlib PSD spectrum canvas for the application.

A log-scaled PSD plot. Each selected hole is drawn as one line in a shared
plot; ``"RSS"`` draws one summed line per hole (no per-axis lines). The
optional dashed reference line is shown only when exactly one hole is selected.
"""

from dataclasses import dataclass
from typing import Literal

import pandas as pd
from matplotlib.figure import Figure

from src.analysis.rms import rss_series
from src.core.settings import Axis
from src.desktop.plots._canvas_base import ScrollPassthroughCanvas
from src.core import strings as S

_FLOOR = 1e-30

# Floor height (px) so the plot keeps a readable size and the enclosing
# QScrollArea scrolls instead of squeezing the canvas.
_MIN_HEIGHT_PX = 300


@dataclass(frozen=True)
class SpectrumPoint:
    """One selected hole to draw in the spectrum.

    Attributes:
        plate_name: Plate the hole belongs to (shown in the legend).
        x_hole, y_hole: Hole coordinates.
        hole_df: The hole's PSD frame (columns ``Frequenz_Hz``, ``PSD_{X,Y,Z}_g2Hz``).
        ref_df: The plate's reference PSD frame, or ``None``.
        color: Explicit line color (``"C0"`` …) coupling the line to its heatmap
            marker; ``None`` lets matplotlib pick from its cycle.
    """

    plate_name: str
    x_hole: int
    y_hole: int
    hole_df: pd.DataFrame
    ref_df: pd.DataFrame | None
    color: str | None = None


def _rss_sum(df: pd.DataFrame) -> pd.Series:  # type: ignore[type-arg]
    """Per-frequency sum of the three axis PSDs, floored for the log y-axis."""
    return rss_series(df).clip(lower=_FLOOR)


class SpectrumCanvas(ScrollPassthroughCanvas):
    """A matplotlib PSD spectrum plot for one or more selected holes."""

    def __init__(self) -> None:
        self._figure = Figure(figsize=(6, 3), layout="constrained")
        super().__init__(self._figure)
        self.axes = self._figure.add_subplot(111)
        self.setMinimumHeight(_MIN_HEIGHT_PX)

    def render_spectrum(
        self,
        points: list[SpectrumPoint],
        *,
        axis: Axis,
        f_min: int,
        f_max: int,
    ) -> None:
        """Draw the spectrum for the given selected holes."""
        self._figure.clear()
        self.axes = self._figure.add_subplot(111)

        show_ref = len(points) == 1
        for p in points:
            if axis == "RSS":
                self._add_rss_line(p, show_ref)
            else:
                self._add_single_axis_line(p, axis, show_ref)

        y_label = (
            S.SPECTRUM_Y_LABEL_RSS if axis == "RSS"
            else S.SPECTRUM_Y_LABEL_TMPL.format(axis=axis)
        )
        self.axes.axvspan(f_min, f_max, facecolor="yellow", alpha=0.1, linewidth=0)
        self.axes.set_yscale("log")
        self.axes.set_xlabel(S.SPECTRUM_X_LABEL)
        self.axes.set_ylabel(y_label)
        self.axes.set_title(self._title(points, axis))
        if points:
            self.axes.legend(loc="upper right", fontsize="small")
        self.draw_idle()

    @staticmethod
    def _title(points: list[SpectrumPoint], axis: Axis) -> str:
        if len(points) == 1:
            p = points[0]
            return S.SPECTRUM_TITLE.format(
                name=p.plate_name, x=p.x_hole, y=p.y_hole, axis=axis
            )
        return S.SPECTRUM_TITLE_MULTI.format(axis=axis, n=len(points))

    def _add_single_axis_line(
        self, p: SpectrumPoint, axis: Literal["X", "Y", "Z"], show_ref: bool
    ) -> None:
        col_psd = f"PSD_{axis}_g2Hz"
        y_series = p.hole_df[col_psd].clip(lower=_FLOOR)
        self.axes.plot(
            p.hole_df["Frequenz_Hz"], y_series,
            linewidth=1.5, color=p.color,
            label=S.SPECTRUM_TRACE_POINT_TMPL.format(
                plate=p.plate_name, x=p.x_hole, y=p.y_hole
            ),
        )
        if show_ref and p.ref_df is not None:
            y_ref = p.ref_df[col_psd].clip(lower=_FLOOR)
            self.axes.plot(
                p.ref_df["Frequenz_Hz"], y_ref,
                color="grey", linewidth=1.2, linestyle="--",
                label=S.SPECTRUM_TRACE_REF,
            )

    def _add_rss_line(self, p: SpectrumPoint, show_ref: bool) -> None:
        self.axes.plot(
            p.hole_df["Frequenz_Hz"], _rss_sum(p.hole_df),
            linewidth=2.0, color=p.color,
            label=S.SPECTRUM_TRACE_POINT_TMPL.format(
                plate=p.plate_name, x=p.x_hole, y=p.y_hole
            ),
        )
        if show_ref and p.ref_df is not None:
            self.axes.plot(
                p.ref_df["Frequenz_Hz"], _rss_sum(p.ref_df),
                color="grey", linewidth=1.2, linestyle="--",
                label=S.SPECTRUM_TRACE_REF,
            )
