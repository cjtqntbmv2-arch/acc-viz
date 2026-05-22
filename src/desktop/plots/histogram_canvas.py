from __future__ import annotations

"""Native matplotlib histogram canvas — desktop replacement for the Plotly histogram.

Mirrors :func:`src.ui.histogram.make_histogram`: non-finite values are dropped,
the bin count is capped at the number of finite values, and an optional dashed
reference line marks the reference value.
"""

import numpy as np
from matplotlib.figure import Figure

from src.desktop.plots._canvas_base import ScrollPassthroughCanvas
from src.ui import strings as S

BAR_COLOR = "#4C78A8"
REF_LINE_COLOR = (1, 1, 0, 0.9)
MEAN_LINE_COLOR = "#D62728"
MEDIAN_LINE_COLOR = "#2CA02C"
SIGMA_LINE_COLOR = "#9467BD"

# Floor height (px) so the plot keeps a readable size and the enclosing
# QScrollArea scrolls instead of squeezing the canvas.
_MIN_HEIGHT_PX = 250


class HistogramCanvas(ScrollPassthroughCanvas):
    """A matplotlib histogram of band-RMS values for one plate."""

    def __init__(self) -> None:
        self._figure = Figure(figsize=(5, 2.6), layout="constrained")
        super().__init__(self._figure)
        self.axes = self._figure.add_subplot(111)
        self.setMinimumHeight(_MIN_HEIGHT_PX)

    def render_values(
        self,
        values: np.ndarray,
        *,
        bins: int,
        normalized: bool,
        ref_value: float | None = None,
        x_range: tuple[float, float] | None = None,
        show_stats: bool = False,
    ) -> None:
        """Draw the histogram. Mirrors ``make_histogram`` semantics."""
        self._figure.clear()
        self.axes = self._figure.add_subplot(111)

        finite = values[np.isfinite(values)]
        if finite.size == 0:
            self.axes.text(
                0.5, 0.5, S.HISTOGRAM_EMPTY,
                ha="center", va="center", transform=self.axes.transAxes,
            )
            self.axes.set_xticks([])
            self.axes.set_yticks([])
            self.draw_idle()
            return

        eff_bins = min(bins, max(1, int(finite.size)))
        label = S.COLORBAR_NORMALIZED if normalized else S.COLORBAR_ABSOLUTE

        self.axes.hist(
            finite,
            bins=eff_bins,
            range=x_range,
            color=BAR_COLOR,
            rwidth=0.95,
        )

        if ref_value is not None:
            self.axes.axvline(ref_value, color=REF_LINE_COLOR, linestyle="--", linewidth=2)

        if show_stats and finite.size >= 2:
            mean = float(np.mean(finite))
            median = float(np.median(finite))
            std = float(np.std(finite))
            self.axes.axvline(
                mean, color=MEAN_LINE_COLOR, linestyle="-", linewidth=2,
                label=S.HISTOGRAM_STAT_MEAN.format(value=mean),
            )
            self.axes.axvline(
                median, color=MEDIAN_LINE_COLOR, linestyle="--", linewidth=2,
                label=S.HISTOGRAM_STAT_MEDIAN.format(value=median),
            )
            self.axes.axvline(mean - std, color=SIGMA_LINE_COLOR, linestyle=":", linewidth=1.5)
            self.axes.axvline(
                mean + std, color=SIGMA_LINE_COLOR, linestyle=":", linewidth=1.5,
                label=S.HISTOGRAM_STAT_SIGMA.format(value=std),
            )
            self.axes.legend(loc="upper right", fontsize="small")

        self.axes.set_xlabel(S.HISTOGRAM_X_LABEL_TMPL.format(label=label))
        self.axes.set_ylabel(S.HISTOGRAM_Y_LABEL)
        if x_range is not None and x_range[0] != x_range[1]:
            self.axes.set_xlim(*x_range)
        self.draw_idle()
