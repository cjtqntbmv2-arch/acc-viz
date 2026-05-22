from __future__ import annotations

"""Native matplotlib PSD spectrum canvas — desktop replacement for the Plotly spectrum.

Mirrors :func:`src.ui.spectrum.render_spectrum`: a log-scaled PSD plot for one
hole, with the selected ``[f_min, f_max]`` band highlighted. Single-axis modes
draw the hole's PSD (plus optional dashed reference); ``"RSS"`` draws the three
per-axis lines and a bold summed line (plus optional summed reference).
"""

from typing import Literal

import pandas as pd
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.figure import Figure

from src.core.settings import Axis
from src.ui import strings as S

_SINGLE_AXES: tuple[Literal["X", "Y", "Z"], ...] = ("X", "Y", "Z")
_FLOOR = 1e-30


def _rss_sum(df: pd.DataFrame) -> pd.Series:
    """Per-frequency sum of the three axis PSDs, floored for the log y-axis."""
    return (df["PSD_X_g2Hz"] + df["PSD_Y_g2Hz"] + df["PSD_Z_g2Hz"]).clip(lower=_FLOOR)


class SpectrumCanvas(FigureCanvasQTAgg):
    """A matplotlib PSD spectrum plot for one hole."""

    def __init__(self) -> None:
        self._figure = Figure(figsize=(6, 3), layout="constrained")
        super().__init__(self._figure)
        self.axes = self._figure.add_subplot(111)

    def render_spectrum(
        self,
        *,
        plate_name: str,
        x_hole: int,
        y_hole: int,
        axis: Axis,
        hole_df: pd.DataFrame,
        ref_df: pd.DataFrame | None,
        f_min: int,
        f_max: int,
    ) -> None:
        """Draw the spectrum for one hole with the selected axis."""
        self._figure.clear()
        self.axes = self._figure.add_subplot(111)

        if axis == "RSS":
            self._add_rss_traces(hole_df, ref_df)
            y_label = S.SPECTRUM_Y_LABEL_RSS
        else:
            self._add_single_axis_traces(hole_df, ref_df, axis, x_hole, y_hole)
            y_label = S.SPECTRUM_Y_LABEL_TMPL.format(axis=axis)

        self.axes.axvspan(f_min, f_max, facecolor="yellow", alpha=0.1, linewidth=0)
        self.axes.set_yscale("log")
        self.axes.set_xlabel(S.SPECTRUM_X_LABEL)
        self.axes.set_ylabel(y_label)
        self.axes.set_title(
            S.SPECTRUM_TITLE.format(name=plate_name, x=x_hole, y=y_hole, axis=axis)
        )
        self.axes.legend(loc="upper right", fontsize="small")
        self.draw_idle()

    def _add_single_axis_traces(
        self,
        hole_df: pd.DataFrame,
        ref_df: pd.DataFrame | None,
        axis: Literal["X", "Y", "Z"],
        x_hole: int,
        y_hole: int,
    ) -> None:
        col_psd = f"PSD_{axis}_g2Hz"
        y_series = hole_df[col_psd].clip(lower=_FLOOR)
        self.axes.plot(
            hole_df["Frequenz_Hz"], y_series,
            linewidth=1.5,
            label=S.SPECTRUM_TRACE_HOLE.format(x=x_hole, y=y_hole),
        )
        if ref_df is not None:
            y_ref = ref_df[col_psd].clip(lower=_FLOOR)
            self.axes.plot(
                ref_df["Frequenz_Hz"], y_ref,
                color="grey", linewidth=1, linestyle="--",
                label=S.SPECTRUM_TRACE_REF,
            )

    def _add_rss_traces(
        self,
        hole_df: pd.DataFrame,
        ref_df: pd.DataFrame | None,
    ) -> None:
        for a in _SINGLE_AXES:
            y_axis = hole_df[f"PSD_{a}_g2Hz"].clip(lower=_FLOOR)
            self.axes.plot(
                hole_df["Frequenz_Hz"], y_axis,
                linewidth=1, alpha=0.7,
                label=S.SPECTRUM_TRACE_AXIS_TMPL.format(axis=a),
            )

        self.axes.plot(
            hole_df["Frequenz_Hz"], _rss_sum(hole_df),
            linewidth=2.5, color="black",
            label=S.SPECTRUM_TRACE_SUM,
        )

        if ref_df is not None:
            self.axes.plot(
                ref_df["Frequenz_Hz"], _rss_sum(ref_df),
                color="grey", linewidth=1.2, linestyle="--",
                label=S.SPECTRUM_TRACE_REF,
            )
