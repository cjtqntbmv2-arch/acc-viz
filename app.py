import math
import platform
import subprocess
import sys

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from src.io.plate_loader import load_plate, LoadResult
from src.analysis.grid import build_grid
from src.analysis.rms import compute_band_rms
from src.analysis.interpolation import interpolate_grid


def pick_folder() -> str | None:
    if platform.system() == "Darwin":
        applescript = (
            'tell application "System Events" to activate\n'
            'set chosenFolder to choose folder with prompt "Ordner wählen"\n'
            'POSIX path of chosenFolder'
        )
        try:
            result = subprocess.run(
                ["osascript", "-e", applescript],
                capture_output=True,
                text=True,
                timeout=300,
            )
        except subprocess.TimeoutExpired:
            return None
        if result.returncode != 0:
            return None
        path = result.stdout.strip().rstrip("/")
        return path or None

    script = (
        "import tkinter as tk;"
        "from tkinter import filedialog;"
        "r=tk.Tk();r.withdraw();r.attributes('-topmost',True);"
        "p=filedialog.askdirectory(parent=r);"
        "print(p)"
    )
    try:
        result = subprocess.run(
            [sys.executable, "-c", script],
            capture_output=True,
            text=True,
            timeout=300,
        )
    except subprocess.TimeoutExpired:
        return None
    path = result.stdout.strip()
    return path or None

st.set_page_config(page_title="Beschleunigungsverteilung", layout="wide")
st.title("Beschleunigungsverteilung — Plattenanalyse")

# --- Sidebar ---
with st.sidebar:
    st.header("Einstellungen")

    if "folder1" not in st.session_state:
        st.session_state.folder1 = ""
    if "folder2" not in st.session_state:
        st.session_state.folder2 = ""

    c1a, c1b = st.columns([3, 1])
    with c1b:
        st.write("")
        st.write("")
        if st.button("📁", key="pick1", help="Ordner wählen"):
            p = pick_folder()
            if p:
                st.session_state.folder1 = p
                st.rerun()
    with c1a:
        folder1 = st.text_input("Platte 1 — Ordnerpfad", key="folder1")

    c2a, c2b = st.columns([3, 1])
    with c2b:
        st.write("")
        st.write("")
        if st.button("📁", key="pick2", help="Ordner wählen"):
            p = pick_folder()
            if p:
                st.session_state.folder2 = p
                st.rerun()
    with c2a:
        folder2 = st.text_input("Platte 2 — Ordnerpfad (optional)", key="folder2")

    f_min, f_max = st.slider(
        "Frequenzband (Hz)",
        min_value=0,
        max_value=25000,
        value=(0, 25000),
        step=100,
    )

    axis = st.radio("Achse", ["X", "Y", "Z"], horizontal=True)

    normalize = st.toggle("Normalisiert (relativ zur Referenz)", value=False)

    shared_scale = st.checkbox("Gemeinsame Farbskala", value=True)

    colorscale = st.selectbox(
        "Farbskala",
        ["Viridis", "Plasma", "Hot", "RdBu", "Cividis", "Turbo", "Inferno"],
    )


# --- Load plates ---
@st.cache_data
def cached_load(folder: str):
    return load_plate(folder)


plates: dict[str, tuple] = {}
if folder1.strip():
    try:
        with st.spinner("Lade Platte 1 …"):
            result = cached_load(folder1.strip())
            plates["Platte 1"] = (result.hole_data, result.ref_df)
            for w in result.warnings:
                st.warning(f"Platte 1: {w}")
    except Exception as exc:
        st.error(f"Platte 1 konnte nicht geladen werden: {exc}")
        st.stop()
if folder2.strip():
    try:
        with st.spinner("Lade Platte 2 …"):
            result = cached_load(folder2.strip())
            plates["Platte 2"] = (result.hole_data, result.ref_df)
            for w in result.warnings:
                st.warning(f"Platte 2: {w}")
    except Exception as exc:
        st.error(f"Platte 2 konnte nicht geladen werden: {exc}")
        st.stop()

if not plates:
    st.info("Bitte mindestens einen Ordnerpfad eingeben.")
    st.stop()

# --- Build grids ---
grids: dict[str, np.ndarray] = {}
ref_rms_values: dict[str, float] = {}
for name, (hole_data, ref_df) in plates.items():
    grids[name] = build_grid(hole_data, ref_df, f_min, f_max, axis, normalize)
    if ref_df is not None:
        val = compute_band_rms(ref_df, f_min, f_max, axis)
        if not math.isnan(val):
            ref_rms_values[name] = val

# --- Interpolate grids ---
def _ref_for_interp(name: str) -> float | None:
    val = ref_rms_values.get(name)
    if val is None:
        return None
    return 1.0 if normalize else val


interp_grids: dict[str, np.ndarray] = {
    name: interpolate_grid(g, _ref_for_interp(name)) for name, g in grids.items()
}

# --- Shared colour scale ---
all_values = [v for g in interp_grids.values() for v in g.flatten() if not np.isnan(v)]
z_min = min(all_values) if all_values else 0.0
z_max = max(all_values) if all_values else 1.0


def make_heatmap(
    grid: np.ndarray,
    title: str,
    use_shared: bool,
    normalized: bool,
    colorscale: str,
    hole_positions: list[tuple[int, int]],
    hole_values: list[float],
    ref_value: float | None,
) -> go.Figure:
    nrows, ncols = grid.shape
    fig = go.Figure(
        go.Heatmap(
            z=grid.T,
            x=list(range(1, nrows + 1)),
            y=list(range(1, ncols + 1)),
            colorscale=colorscale,
            zmin=z_min if use_shared else None,
            zmax=z_max if use_shared else None,
            colorbar=dict(title="Normalisiert" if normalized else "g RMS"),
            hoverongaps=False,
            hovertemplate=f"x=%{{x}}, y=%{{y}}<br>Interpoliert ({'Normalisiert' if normalized else 'g RMS'})=%{{z:.4f}}<extra></extra>",
        )
    )
    label = "Normalisiert" if normalized else "g RMS"
    fig.add_trace(go.Scatter(
        x=[x for (x, _) in hole_positions],
        y=[y for (_, y) in hole_positions],
        mode="markers",
        marker=dict(
            size=8,
            color="rgba(255,255,255,0.4)",
            line=dict(color="rgba(0,0,0,0.7)", width=1.5),
        ),
        customdata=hole_values,
        hovertemplate=f"x=%{{x}}, y=%{{y}}<br>{label}=%{{customdata:.4f}}<extra></extra>",
        showlegend=False,
    ))
    if ref_value is not None:
        x_center = (nrows + 1) / 2
        y_center = (ncols + 1) / 2
        fig.add_trace(go.Scatter(
            x=[x_center],
            y=[y_center],
            mode="markers",
            marker=dict(
                size=14,
                symbol="star",
                color="rgba(255,255,0,0.9)",
                line=dict(color="black", width=1.5),
            ),
            customdata=[ref_value],
            hovertemplate=f"Referenz (Mitte)<br>{label}=%{{customdata:.4f}}<extra></extra>",
            showlegend=False,
        ))

    fig.update_layout(
        title=title,
        xaxis_title="x-Bohrung",
        yaxis_title="y-Bohrung",
        height=600,
    )
    fig.update_yaxes(scaleanchor="x", scaleratio=1, constrain="domain", autorange="reversed")
    fig.update_xaxes(constrain="domain")
    return fig


# --- Render heatmaps ---
plate_names = list(grids.keys())
cols = st.columns(len(plate_names))
click_state: dict[str, tuple[int, int] | None] = {}

for col, name in zip(cols, plate_names):
    with col:
        ref_val = ref_rms_values.get(name)
        if ref_val is not None:
            label = "Normalisiert (Ref = 1.0)" if normalize else f"{ref_val:.4f} g RMS"
            st.metric(f"{name} — Referenz", label)

        hole_data_plate, _ = plates[name]
        sparse_grid = grids[name]
        positions_valid = []
        values = []
        for (x, y) in hole_data_plate.keys():
            val = float(sparse_grid[x - 1, y - 1])
            if not np.isnan(val):
                positions_valid.append((x, y))
                values.append(val)

        if ref_val is None:
            ref_marker_value = None
        else:
            ref_marker_value = 1.0 if normalize else ref_val

        fig = make_heatmap(
            interp_grids[name],
            name,
            shared_scale,
            normalize,
            colorscale,
            positions_valid,
            values,
            ref_marker_value,
        )
        event = st.plotly_chart(fig, on_select="rerun", key=f"heatmap_{name}", use_container_width=True)
        clicked = None
        if event and event["selection"] and event["selection"]["points"]:
            pt = event["selection"]["points"][0]
            clicked = (int(pt["x"]), int(pt["y"]))  # (x_hole, y_hole)
        click_state[name] = clicked

# --- Spectrum detail ---
for name, clicked in click_state.items():
    if clicked is None:
        continue
    x_hole, y_hole = clicked
    hole_data, ref_df = plates[name]
    if (x_hole, y_hole) not in hole_data:
        st.warning(f"{name}: Keine Messdaten für Bohrung ({x_hole}, {y_hole}).")
        continue

    df_hole = hole_data[(x_hole, y_hole)]
    col_psd = f"PSD_{axis}_g2Hz"
    st.subheader(f"{name} — Bohrung ({x_hole}, {y_hole}) · Achse {axis}")

    spec_fig = go.Figure()
    spec_fig.add_trace(go.Scatter(
        x=df_hole["Frequenz_Hz"],
        y=df_hole[col_psd],
        name=f"Bohrung ({x_hole}, {y_hole})",
        line=dict(width=1.5),
    ))
    if ref_df is not None:
        spec_fig.add_trace(go.Scatter(
            x=ref_df["Frequenz_Hz"],
            y=ref_df[col_psd],
            name="Referenz",
            line=dict(color="grey", width=1, dash="dash"),
        ))
    spec_fig.add_vrect(x0=f_min, x1=f_max, fillcolor="yellow", opacity=0.1, line_width=0)
    spec_fig.update_layout(
        xaxis_title="Frequenz (Hz)",
        yaxis_title=f"PSD {axis} (g²/Hz)",
        yaxis_type="log",
        height=350,
        legend=dict(orientation="h"),
    )
    st.plotly_chart(spec_fig, use_container_width=True)

# --- CSV Export ---
rows = []
for name, (hole_data, ref_df) in plates.items():
    ref_rms_csv = (
        compute_band_rms(ref_df, f_min, f_max, axis)
        if ref_df is not None
        else None
    )
    for (x, y), df in sorted(hole_data.items()):
        rms_abs = compute_band_rms(df, f_min, f_max, axis)
        rms_norm = (
            rms_abs / ref_rms_csv
            if (ref_rms_csv is not None and not math.isnan(ref_rms_csv) and ref_rms_csv > 0 and not math.isnan(rms_abs))
            else ""
        )
        rows.append({
            "plate": name,
            "x": x,
            "y": y,
            "axis": axis,
            "f_min_hz": f_min,
            "f_max_hz": f_max,
            "band_rms_abs": rms_abs,
            "band_rms_normalized": rms_norm,
        })

csv_bytes = pd.DataFrame(rows).to_csv(index=False).encode("utf-8")
st.sidebar.download_button(
    label="CSV exportieren",
    data=csv_bytes,
    file_name="beschleunigung_export.csv",
    mime="text/csv",
)
