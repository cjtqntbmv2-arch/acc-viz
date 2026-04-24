from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

import streamlit as st

from src.platform_utils.folder_picker import pick_folder
from src.ui import strings as S

Axis = Literal["X", "Y", "Z"]


@dataclass(frozen=True)
class Settings:
    folders: list[tuple[str, str]]  # (label, raw path)
    f_min: int
    f_max: int
    axis: Axis
    normalize: bool
    shared_scale: bool
    colorscale: str


_COLORSCALES = ["Viridis", "Plasma", "Hot", "RdBu", "Cividis", "Turbo", "Inferno"]


def _normalize_path(raw: str) -> str:
    return raw.strip().strip('"').strip("'")


def _folder_input(label: str, key: str) -> str:
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
        st.text_input(label, key=key)
    return _normalize_path(st.session_state[key])


def render_sidebar() -> Settings:
    with st.sidebar:
        st.header(S.SIDEBAR_HEADER)
        p1 = _folder_input(S.FOLDER_PLATE_1, "folder1")
        p2 = _folder_input(S.FOLDER_PLATE_2, "folder2")

        f_min, f_max = st.slider(
            S.FREQUENCY_BAND, min_value=0, max_value=25000,
            value=(0, 25000), step=100,
        )
        axis = st.radio(S.AXIS, ["X", "Y", "Z"], horizontal=True)
        normalize = st.toggle(S.NORMALIZE, value=False)
        shared_scale = st.checkbox(S.SHARED_SCALE, value=True)
        colorscale = st.selectbox(S.COLORSCALE, _COLORSCALES)

    folders: list[tuple[str, str]] = []
    if p1:
        folders.append(("Platte 1", p1))
    if p2:
        folders.append(("Platte 2", p2))

    return Settings(
        folders=folders,
        f_min=int(f_min),
        f_max=int(f_max),
        axis=axis,  # type: ignore[arg-type]
        normalize=normalize,
        shared_scale=shared_scale,
        colorscale=colorscale,
    )
