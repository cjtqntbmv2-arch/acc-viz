from __future__ import annotations

"""Streamlit sidebar controls.

The :class:`Settings` snapshot now lives in the frontend-agnostic
:mod:`src.core.settings`; it is re-exported here for backward compatibility.
"""

from typing import cast, get_args

import streamlit as st

from src.analysis.interpolation import InterpolationMethod
from src.core.colorscales import COLORSCALES
from src.core.settings import Axis, Settings, normalize_path
from src.platform_utils.folder_picker import pick_folder
from src.ui import strings as S

__all__ = ["Axis", "Settings", "render_sidebar"]


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
    return normalize_path(st.session_state[key])


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
        colorscale = st.selectbox(S.COLORSCALE, COLORSCALES, help=S.HELP_COLORSCALE)

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
