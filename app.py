from __future__ import annotations

import streamlit as st

from src.core.pipeline import (
    PlateEntry,
    analyze,
    load_plates,
    measured_points,
    ref_marker,
)
from src.core.settings import Settings
from src.logging_setup import get_logger
from src.ui import strings as S
from src.ui.export import render_csv_export
from src.ui.heatmap import make_heatmap
from src.ui.histogram import make_histogram
from src.ui.sidebar import render_sidebar
from src.ui.spectrum import render_spectrum

_LOG = get_logger(__name__)

st.set_page_config(page_title=S.PAGE_TITLE, layout="wide")
st.title(S.APP_TITLE)

settings: Settings = render_sidebar()

if not settings.folders:
    st.info(S.WAITING_FOR_FOLDER)
    st.stop()

with st.spinner(S.LOADING_PLATE.format(label="…")):
    load = load_plates(settings.folders)

for warning in load.warnings:
    st.warning(warning)
for msg in load.errors:
    st.error(msg)

plates: dict[str, PlateEntry] = load.plates
if not plates:
    # Nothing usable loaded — show the errors above and halt.
    st.stop()

result = analyze(plates, settings)
grids = result.grids
interp_grids = result.interp_grids
ref_rms = result.ref_rms
z_range = result.z_range
hist_range = result.hist_range

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
            st.metric(S.REF_METRIC_HEADER.format(name=name), label, help=S.HELP_REF_METRIC)

        hole_data_plate, _ = plates[name]
        sparse_grid = grids[name]
        positions, values = measured_points(sparse_grid, hole_data_plate)
        marker = ref_marker(ref_val, normalize=settings.normalize)

        fig = make_heatmap(
            interp_grids[name],
            title=name,
            colorscale=settings.colorscale,
            normalized=settings.normalize,
            hole_positions=positions,
            hole_values=values,
            ref_value=marker,
            z_range=z_range,
        )
        event = st.plotly_chart(
            fig,
            on_select="rerun",
            selection_mode=("points",),
            key=f"heatmap_{name}",
            use_container_width=True,
        )
        st.caption(S.CAPTION_HEATMAP_LEGEND)

        hist_fig = make_histogram(
            grids[name].ravel(),
            bins=settings.histogram_bins,
            normalized=settings.normalize,
            ref_value=marker,
            x_range=hist_range if settings.shared_scale else None,
            show_stats=settings.histogram_stats,
        )
        st.plotly_chart(hist_fig, use_container_width=True, key=f"hist_{name}")

        clicked: tuple[int, int] | None = None
        points = getattr(getattr(event, "selection", None), "points", None)
        if points is None and isinstance(event, dict):
            # Streamlit <1.36 returns a plain dict instead of an attribute-accessible object.
            points = event.get("selection", {}).get("points") if event.get("selection") else None
        if points:
            pt = points[0]
            try:
                clicked = (int(pt["x"]), int(pt["y"]))
            except (KeyError, TypeError, ValueError) as exc:
                _LOG.debug("Could not extract click coordinates from %r: %s", pt, exc)
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
