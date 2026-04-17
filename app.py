import math
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from data_loader import load_plate
from processing import build_grid, compute_band_rms, interpolate_grid

st.set_page_config(page_title="Beschleunigungsverteilung", layout="wide")
st.title("Beschleunigungsverteilung — Plattenanalyse")

# --- Sidebar ---
with st.sidebar:
    st.header("Einstellungen")

    folder1 = st.text_input("Platte 1 — Ordnerpfad", value="")
    folder2 = st.text_input("Platte 2 — Ordnerpfad (optional)", value="")

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
            plates["Platte 1"] = cached_load(folder1.strip())
    except Exception as exc:
        st.error(f"Platte 1 konnte nicht geladen werden: {exc}")
        st.stop()
if folder2.strip():
    try:
        with st.spinner("Lade Platte 2 …"):
            plates["Platte 2"] = cached_load(folder2.strip())
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
interp_grids: dict[str, np.ndarray] = {
    name: interpolate_grid(g) for name, g in grids.items()
}

# --- Shared colour scale ---
all_values = [v for g in grids.values() for v in g.flatten() if not np.isnan(v)]
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
) -> go.Figure:
    nrows, ncols = grid.shape
    fig = go.Figure(
        go.Heatmap(
            z=grid,
            x=list(range(1, ncols + 1)),
            y=list(range(1, nrows + 1)),
            colorscale=colorscale,
            zmin=z_min if use_shared else None,
            zmax=z_max if use_shared else None,
            colorbar=dict(title="Normalisiert" if normalized else "g RMS"),
            hoverongaps=False,
        )
    )
    label = "Normalisiert" if normalized else "g RMS"
    fig.add_trace(go.Scatter(
        x=[y for (_, y) in hole_positions],
        y=[x for (x, _) in hole_positions],
        mode="markers",
        marker=dict(
            size=8,
            color="rgba(255,255,255,0.4)",
            line=dict(color="rgba(0,0,0,0.7)", width=1.5),
        ),
        customdata=hole_values,
        hovertemplate=f"x=%{{y}}, y=%{{x}}<br>{label}=%{{customdata:.4f}}<extra></extra>",
        showlegend=False,
    ))
    fig.update_layout(
        title=title,
        xaxis_title="y-Bohrung",
        yaxis_title="x-Bohrung",
        height=500,
    )
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
        positions = list(hole_data_plate.keys())  # [(x_bohrung, y_bohrung), ...]
        values = [
            float(sparse_grid[x - 1, y - 1])
            for (x, y) in positions
            if not np.isnan(sparse_grid[x - 1, y - 1])
        ]
        positions_valid = [
            (x, y) for (x, y) in positions
            if not np.isnan(sparse_grid[x - 1, y - 1])
        ]

        fig = make_heatmap(
            interp_grids[name],
            name,
            shared_scale,
            normalize,
            colorscale,
            positions_valid,
            values,
        )
        event = st.plotly_chart(fig, on_select="rerun", key=f"heatmap_{name}", use_container_width=True)
        clicked = None
        if event and event["selection"] and event["selection"]["points"]:
            pt = event["selection"]["points"][0]
            clicked = (int(pt["y"]), int(pt["x"]))  # (x_hole, y_hole)
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
