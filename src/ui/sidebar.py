from __future__ import annotations

"""Streamlit sidebar controls and the immutable :class:`Settings` snapshot."""

from dataclasses import dataclass
from typing import Literal, cast, get_args

import streamlit as st

from src.analysis.interpolation import InterpolationMethod
from src.platform_utils.folder_picker import pick_folder
from src.ui import strings as S

Axis = Literal["X", "Y", "Z", "RSS"]


@dataclass(frozen=True)
class Settings:
    """Immutable snapshot of all user-selected analysis settings.

    Attributes:
        folders: List of ``(label, raw_path)`` tuples for every non-empty
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
        colorscale: Plotly colorscale identifier selected by the user.
        histogram_bins: Upper bound on the histogram bin count. The actual
            bin count is capped at the number of measured holes.
    """

    folders: list[tuple[str, str]]  # (label, raw path)
    f_min: int
    f_max: int
    axis: Axis
    normalize: bool
    shared_scale: bool
    colorscale: str
    interpolate: bool = True
    histogram_bins: int = 20
    interp_method: InterpolationMethod = "linear"


_COLORSCALES: tuple[str, ...] = (
    "Viridis", "Plasma", "Hot", "RdBu", "Cividis", "Turbo", "Inferno",
)


def _normalize_path(raw: str) -> str:
    """Strip surrounding whitespace and matching single/double quotes.

    Users often paste paths from terminals or file managers with enclosing
    quotes; this helper makes those inputs usable.

    Args:
        raw: Raw string as typed or pasted by the user.

    Returns:
        The cleaned path string.
    """
    return raw.strip().strip('"').strip("'")


def _folder_input(label: str, key: str, help_text: str | None = None) -> str:
    """Render a text input paired with a native folder picker button.

    Uses Streamlit session state (``key``) to persist the selection across
    reruns. Clicking the picker triggers a native dialog and writes the chosen
    path back into session state.

    Args:
        label: Label displayed next to the text input.
        key: Unique session-state key backing this input.
        help_text: Optional tooltip shown as a ``?`` icon next to the text
            input label.

    Returns:
        The normalized path currently stored under ``key``.
    """
    if key not in st.session_state:
        st.session_state[key] = ""
    col_a, col_b = st.columns([3, 1])
    with col_b:
        st.write("")
        st.write("")
        if st.button("📁", key=f"pick_{key}", help=S.PICK_FOLDER):
            picked = pick_folder()
            if picked:
                st.session_state[key] = picked
                st.rerun()
    with col_a:
        st.text_input(label, key=key, help=help_text)
    return _normalize_path(st.session_state[key])


def render_sidebar() -> Settings:
    """Render all sidebar widgets and return the user's current selections.

    Must be called from within a Streamlit script run. Only folder inputs
    that produced non-empty paths are included in :attr:`Settings.folders`.

    Returns:
        A frozen :class:`Settings` instance describing the current UI state.
    """
    with st.sidebar:
        st.header(S.SIDEBAR_HEADER)
        p1 = _folder_input(S.FOLDER_PLATE_1, "accviz_folder1", help_text=S.HELP_FOLDER_PLATE)
        p2 = _folder_input(S.FOLDER_PLATE_2, "accviz_folder2", help_text=S.HELP_FOLDER_PLATE)

        f_min, f_max = st.slider(
            S.FREQUENCY_BAND, min_value=0, max_value=25000,
            value=(0, 25000), step=100,
            help=S.HELP_FREQUENCY_BAND,
        )
        axis_raw = st.radio(
            S.AXIS, ["X", "Y", "Z", "RSS"], horizontal=True, help=S.HELP_AXIS,
        )
        if axis_raw not in get_args(Axis):
            axis_raw = "X"
        axis: Axis = cast(Axis, axis_raw)
        normalize = st.toggle(S.NORMALIZE, value=False, help=S.HELP_NORMALIZE)
        interpolate = st.toggle(S.INTERPOLATE, value=True, help=S.HELP_INTERPOLATE)
        # Single source of truth for the label <-> Literal mapping.
        method_labels: dict[str, InterpolationMethod] = {
            S.INTERP_METHOD_LINEAR: "linear",
            S.INTERP_METHOD_TPS: "tps",
        }
        method_label = st.radio(
            S.INTERP_METHOD,
            tuple(method_labels.keys()),
            horizontal=True,
            disabled=not interpolate,
            help=S.HELP_INTERP_METHOD,
        )
        interp_method: InterpolationMethod = method_labels.get(
            method_label or "", "linear"
        )
        histogram_bins = st.slider(
            S.HISTOGRAM_BINS, min_value=5, max_value=50,
            value=20, step=1, help=S.HELP_HISTOGRAM_BINS,
        )
        shared_scale = st.checkbox(S.SHARED_SCALE, value=True, help=S.HELP_SHARED_SCALE)
        colorscale = st.selectbox(S.COLORSCALE, _COLORSCALES, help=S.HELP_COLORSCALE)

    folders: list[tuple[str, str]] = []
    if p1:
        folders.append(("Platte 1", p1))
    if p2:
        folders.append(("Platte 2", p2))

    return Settings(
        folders=folders,
        f_min=int(f_min),
        f_max=int(f_max),
        axis=axis,
        normalize=normalize,
        shared_scale=shared_scale,
        colorscale=colorscale,
        interpolate=interpolate,
        histogram_bins=int(histogram_bins),
        interp_method=interp_method,
    )
