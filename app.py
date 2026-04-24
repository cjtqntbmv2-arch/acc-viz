from __future__ import annotations

import math

import numpy as np
import streamlit as st

from src.analysis.grid import build_grid
from src.analysis.interpolation import interpolate_grid
from src.analysis.rms import compute_band_rms
from src.io.plate_loader import LoadResult, load_plate
from src.io.schema import AccVizError
from src.ui import strings as S
from src.ui.errors import format_error
from src.ui.export import render_csv_export
from src.ui.heatmap import make_heatmap
from src.ui.sidebar import Settings, render_sidebar
from src.ui.spectrum import render_spectrum

st.set_page_config(page_title=S.PAGE_TITLE, layout="wide")
st.title(S.APP_TITLE)

settings: Settings = render_sidebar()

if not settings.folders:
    st.info(S.WAITING_FOR_FOLDER)
    st.stop()


def _folder_mtime_token(folder: str) -> float:
    from pathlib import Path
    p = Path(folder)
    if not p.exists():
        return 0.0
    mtimes = [f.stat().st_mtime for f in p.glob("*.csv")]
    return max(mtimes) if mtimes else 0.0


@st.cache_data(show_spinner=False)
def _cached_load(folder: str, mtime_token: float) -> LoadResult:
    return load_plate(folder)


plates: dict[str, tuple] = {}
for label, folder in settings.folders:
    try:
        with st.spinner(S.LOADING_PLATE.format(label=label)):
            result = _cached_load(folder, _folder_mtime_token(folder))
    except AccVizError as exc:
        st.error(format_error(exc, plate_label=label))
        st.stop()
    for w in result.warnings:
        st.warning(f"{label}: {w}")
    plates[label] = (result.hole_data, result.ref_df)

grids: dict[str, np.ndarray] = {}
ref_rms: dict[str, float] = {}
for name, (hole_data, ref_df) in plates.items():
    grids[name] = build_grid(hole_data, ref_df, settings.f_min, settings.f_max, settings.axis, settings.normalize)
    if ref_df is not None:
        val = compute_band_rms(ref_df, settings.f_min, settings.f_max, settings.axis)
        if not math.isnan(val):
            ref_rms[name] = val


def _ref_for_interp(name: str) -> float | None:
    val = ref_rms.get(name)
    if val is None:
        return None
    return 1.0 if settings.normalize else val


interp_grids = {name: interpolate_grid(g, _ref_for_interp(name)) for name, g in grids.items()}

all_values = [v for g in interp_grids.values() for v in g.flatten() if not np.isnan(v)]
z_range = (min(all_values), max(all_values)) if (settings.shared_scale and all_values) else None

cols = st.columns(len(plates))
click_state: dict[str, tuple[int, int] | None] = {}

for col, name in zip(cols, plates.keys()):
    with col:
        ref_val = ref_rms.get(name)
        if ref_val is not None:
            label = (
                S.REF_METRIC_LABEL_NORMALIZED
                if settings.normalize
                else S.REF_METRIC_LABEL_ABS.format(value=ref_val)
            )
            st.metric(S.REF_METRIC_HEADER.format(name=name), label)

        hole_data_plate, _ = plates[name]
        sparse_grid = grids[name]
        positions, values = [], []
        for (x, y) in hole_data_plate.keys():
            v = float(sparse_grid[x - 1, y - 1])
            if not np.isnan(v):
                positions.append((x, y))
                values.append(v)

        if ref_val is None:
            ref_marker = None
        else:
            ref_marker = 1.0 if settings.normalize else ref_val

        fig = make_heatmap(
            interp_grids[name],
            title=name,
            colorscale=settings.colorscale,
            normalized=settings.normalize,
            hole_positions=positions,
            hole_values=values,
            ref_value=ref_marker,
            z_range=z_range,
        )
        event = st.plotly_chart(fig, on_select="rerun", key=f"heatmap_{name}", use_container_width=True)
        clicked = None
        if event and event["selection"] and event["selection"]["points"]:
            pt = event["selection"]["points"][0]
            clicked = (int(pt["x"]), int(pt["y"]))
        click_state[name] = clicked

for name, clicked in click_state.items():
    if clicked is None:
        continue
    x_hole, y_hole = clicked
    hole_data, ref_df = plates[name]
    if (x_hole, y_hole) not in hole_data:
        st.warning(S.WARN_NO_DATA_FOR_HOLE.format(name=name, x=x_hole, y=y_hole))
        continue
    render_spectrum(
        plate_name=name,
        x_hole=x_hole,
        y_hole=y_hole,
        axis=settings.axis,
        hole_df=hole_data[(x_hole, y_hole)],
        ref_df=ref_df,
        f_min=settings.f_min,
        f_max=settings.f_max,
    )

render_csv_export(plates, f_min=settings.f_min, f_max=settings.f_max, axis=settings.axis)
