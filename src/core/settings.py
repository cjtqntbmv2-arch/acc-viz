from __future__ import annotations

"""Immutable, UI-agnostic snapshot of all user-selected analysis settings.

This module is intentionally free of any frontend dependency (no Qt, no
matplotlib) so it can be shared by every frontend and unit-tested in isolation.
"""

from dataclasses import dataclass
from typing import Literal

from src.analysis.interpolation import InterpolationMethod

Axis = Literal["X", "Y", "Z", "RSS"]


@dataclass(frozen=True)
class Settings:
    """Immutable snapshot of all user-selected analysis settings.

    Attributes:
        folders: Tuple of ``(label, raw_path)`` tuples for every non-empty
            folder input the user provided.
        f_min: Lower bound of the selected frequency band in Hz.
        f_max: Upper bound of the selected frequency band in Hz.
        axis: Axis (``"X"``, ``"Y"``, ``"Z"``, or ``"RSS"``) used for the
            RMS computation. ``"RSS"`` entspricht der Wurzel der Summe der
            Quadrate der drei Einzelachsen-gRMS-Werte (Root Sum of Squares).
        normalize: Whether to normalize hole RMS values against the reference
            measurement.
        interpolate: Whether to fill missing heatmap cells via
            :func:`interpolate_grid`. When ``False`` only measured cells are
            shown; missing cells are rendered as transparent gaps.
        interp_method: Selected interpolation algorithm for filling missing
            heatmap cells: ``"linear"`` (Delaunay + nearest fallback) or
            ``"tps"`` (thin-plate-spline). Ignored when :attr:`interpolate`
            is ``False``.
        shared_scale: Whether heatmaps should share a common color scale
            across plates. Also drives the shared x-axis range for the
            per-plate histograms.
        colorscale: Colorscale identifier selected by the user.
        histogram_bins: Upper bound on the histogram bin count. The actual
            bin count is capped at the number of measured holes.
        histogram_stats: Whether to overlay mean, median, and ±1σ marker lines
            on the per-plate histograms. Pure display flag — does not affect the
            computed analysis.
        show_histogram: Whether to show the per-plate histogram below each
            heatmap. Pure display flag — does not affect the computed analysis.
    """

    folders: tuple[tuple[str, str], ...]  # (label, raw path)
    f_min: int
    f_max: int
    axis: Axis
    normalize: bool
    shared_scale: bool
    colorscale: str
    interpolate: bool = True
    histogram_bins: int = 20
    histogram_stats: bool = True
    interp_method: InterpolationMethod = "linear"
    show_histogram: bool = True


def normalize_path(raw: str) -> str:
    """Strip surrounding whitespace and matching single/double quotes.

    Users often paste paths from terminals or file managers with enclosing
    quotes; this helper makes those inputs usable.
    """
    return raw.strip().strip('"').strip("'")
