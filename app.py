from __future__ import annotations

import math
from pathlib import Path

import numpy as np
import pandas as pd
import streamlit as st

from src.analysis.grid import build_grid
from src.analysis.interpolation import interpolate_grid
from src.analysis.rms import compute_band_rms
from src.io.plate_loader import LoadResult, load_plate
from src.io.schema import AccVizError
from src.logging_setup import get_logger
from src.ui import strings as S
from src.ui.errors import format_error
from src.ui.export import render_csv_export
from src.ui.heatmap import make_heatmap
from src.ui.sidebar import Settings, render_sidebar
from src.ui.spectrum import render_spectrum

PlateEntry = tuple[dict[tuple[int, int], pd.DataFrame], pd.DataFrame | None]

_LOG = get_logger(__name__)

st.set_page_config(page_title=S.PAGE_TITLE, layout="wide")
st.title(S.APP_TITLE)

settings: Settings = render_sidebar()

if not settings.folders:
    st.info(S.WAITING_FOR_FOLDER)
    st.stop()


def _folder_mtime_token(folder: str) -> float:
    """Return newest ``*.csv`` mtime in ``folder`` for cache invalidation."""
    p = Path(folder)
    if not p.exists():
        return 0.0
    # Case-insensitive match: Linux/macOS are case-sensitive by default while the
    # plate loader accepts any case, so a simple "*.csv" glob would miss files.
    mtimes = [f.stat().st_mtime for f in p.iterdir() if f.is_file() and f.suffix.lower() == ".csv"]
    return max(mtimes) if mtimes else 0.0


@st.cache_data(show_spinner=False)
def _cached_load(folder: str, mtime_token: float) -> LoadResult:
    return load_plate(folder)


plates: dict[str, PlateEntry] = {}
load_errors: list[str] = []
for label, folder in settings.folders:
    try:
        with st.spinner(S.LOADING_PLATE.format(label=label)):
            result = _cached_load(folder, _folder_mtime_token(folder))
    except AccVizError as exc:
        _LOG.warning("Plate %s load failed: %s", label, exc)
        load_errors.append(format_error(exc, plate_label=label))
        continue
    except Exception as exc:  # defensive: surface unexpected errors to the user
        _LOG.exception("Unexpected error loading plate %s", label)
        load_errors.append(S.ERROR_GENERIC_PLATE.format(label=label, detail=str(exc)))
        continue
    for w in result.warnings:
        st.warning(f"{label}: {w}")
    plates[label] = (result.hole_data, result.ref_df)

for msg in load_errors:
    st.error(msg)

if not plates:
    # Nothing usable loaded — show the errors above and halt.
    st.stop()

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

if interp_grids:
    stacked = np.concatenate([g.ravel() for g in interp_grids.values()])
    finite = stacked[np.isfinite(stacked)]
    z_range = (float(finite.min()), float(finite.max())) if settings.shared_scale and finite.size else None
else:
    z_range = None

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
        positions: list[tuple[int, int]] = []
        values: list[float] = []
        for (x, y) in hole_data_plate.keys():
            v = float(sparse_grid[x - 1, y - 1])
            if not np.isnan(v):
                positions.append((x, y))
                values.append(v)

        if ref_val is None:
            ref_marker: float | None = None
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
        event = st.plotly_chart(
            fig,
            on_select="rerun",
            selection_mode=("points",),
            key=f"heatmap_{name}",
            use_container_width=True,
        )
        st.caption(S.CAPTION_HEATMAP_LEGEND)
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
