from __future__ import annotations

"""Frontend-agnostic orchestration of the load → grid → interpolate pipeline.

Extracted from the original Streamlit ``app.py`` so the exact same computation
can drive any frontend (Streamlit, Qt) and be unit-tested without a UI. No
Streamlit / Qt imports here on purpose.
"""

import math
from collections import OrderedDict
from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import pandas as pd

from src.analysis.grid import build_grid
from src.analysis.interpolation import interpolate_grid
from src.analysis.rms import compute_band_rms
from src.core.settings import Settings
from src.io.plate_loader import LoadResult, load_plate
from src.io.schema import AccVizError
from src.logging_setup import get_logger
from src.ui import strings as S
from src.ui.errors import format_error

_LOG = get_logger(__name__)

# A loaded plate: mapping of (x, y) -> measurement DataFrame, plus optional ref.
PlateEntry = tuple[dict[tuple[int, int], pd.DataFrame], pd.DataFrame | None]


@dataclass(frozen=True)
class PlateLoad:
    """Result of loading a set of plate folders.

    Attributes:
        plates: Mapping from plate label to its ``(hole_data, ref_df)`` tuple.
            Only successfully loaded plates appear here.
        warnings: Non-fatal, user-facing messages (already prefixed with the
            plate label, e.g. ``"Platte 1: Referenz.csv nicht gefunden …"``).
        errors: User-facing error strings for plates that failed to load.
    """

    plates: dict[str, PlateEntry]
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class Analysis:
    """Computed grids and color-scale metadata for a set of loaded plates.

    Attributes:
        grids: Per-plate sparse grid of band-RMS values (NaN for missing holes).
        interp_grids: Per-plate grid after optional interpolation.
        ref_rms: Per-plate reference band-RMS (only when a usable reference
            measurement was present).
        z_range: Shared ``(zmin, zmax)`` color range when
            :attr:`Settings.shared_scale` is set and finite data exists,
            otherwise ``None``.
    """

    grids: dict[str, np.ndarray]
    interp_grids: dict[str, np.ndarray]
    ref_rms: dict[str, float]
    z_range: tuple[float, float] | None


# --- loading (with mtime-based caching, replacing st.cache_data) -----------

# Bounded LRU keyed by (folder, newest-csv-mtime). Bounded so a long session of
# browsing many folders (each LoadResult holds full DataFrames) cannot grow
# memory without limit.
_CACHE_MAXSIZE = 8
_LOAD_CACHE: OrderedDict[tuple[str, float], LoadResult] = OrderedDict()


def _folder_mtime_token(folder: str) -> float:
    """Return newest ``*.csv`` mtime in ``folder`` for cache invalidation."""
    p = Path(folder)
    if not p.exists():
        return 0.0
    # Case-insensitive match: Linux/macOS are case-sensitive by default while the
    # plate loader accepts any case, so a simple "*.csv" glob would miss files.
    mtimes = [f.stat().st_mtime for f in p.iterdir() if f.is_file() and f.suffix.lower() == ".csv"]
    return max(mtimes) if mtimes else 0.0


def _cached_load(folder: str) -> LoadResult:
    """Load a plate folder, memoized (LRU) by (folder, newest-csv-mtime)."""
    token = _folder_mtime_token(folder)
    key = (folder, token)
    cached = _LOAD_CACHE.get(key)
    if cached is not None:
        _LOAD_CACHE.move_to_end(key)
        return cached
    result = load_plate(folder)
    _LOAD_CACHE[key] = result
    if len(_LOAD_CACHE) > _CACHE_MAXSIZE:
        _LOAD_CACHE.popitem(last=False)
    return result


def load_plates(folders: list[tuple[str, str]]) -> PlateLoad:
    """Load every plate folder, collecting warnings and user-facing errors.

    Mirrors the original Streamlit load loop: each folder is loaded (with
    mtime-based caching), warnings are prefixed with the plate label, and load
    failures are turned into localized error strings instead of raising.

    Args:
        folders: List of ``(label, raw_path)`` tuples.

    Returns:
        A :class:`PlateLoad` with the successfully loaded plates plus any
        warnings and errors.
    """
    plates: dict[str, PlateEntry] = {}
    warnings: list[str] = []
    errors: list[str] = []

    for label, folder in folders:
        try:
            result = _cached_load(folder)
        except AccVizError as exc:
            _LOG.warning("Plate %s load failed: %s", label, exc)
            errors.append(format_error(exc, plate_label=label))
            continue
        except Exception as exc:  # defensive: surface unexpected errors
            _LOG.exception("Unexpected error loading plate %s", label)
            errors.append(S.ERROR_GENERIC_PLATE.format(label=label, detail=str(exc)))
            continue
        for w in result.warnings:
            warnings.append(f"{label}: {w}")
        plates[label] = (result.hole_data, result.ref_df)

    return PlateLoad(plates=plates, warnings=warnings, errors=errors)


# --- analysis --------------------------------------------------------------

def analyze(plates: dict[str, PlateEntry], settings: Settings) -> Analysis:
    """Compute per-plate grids, reference RMS, interpolation and shared z-range.

    Mirrors the original Streamlit compute block exactly.

    Args:
        plates: Mapping from plate label to ``(hole_data, ref_df)`` tuples, as
            produced by :func:`load_plates`.
        settings: The analysis settings driving the computation.

    Returns:
        An :class:`Analysis` with grids, interpolated grids, reference RMS and
        the optional shared color range.
    """
    grids: dict[str, np.ndarray] = {}
    ref_rms: dict[str, float] = {}
    for name, (hole_data, ref_df) in plates.items():
        grids[name] = build_grid(
            hole_data, ref_df, settings.f_min, settings.f_max, settings.axis, settings.normalize
        )
        if ref_df is not None:
            val = compute_band_rms(ref_df, settings.f_min, settings.f_max, settings.axis)
            if not math.isnan(val):
                ref_rms[name] = val

    def _ref_for_interp(name: str) -> float | None:
        val = ref_rms.get(name)
        if val is None:
            return None
        return 1.0 if settings.normalize else val

    if settings.interpolate:
        interp_grids = {
            name: interpolate_grid(g, _ref_for_interp(name), method=settings.interp_method)
            for name, g in grids.items()
        }
    else:
        interp_grids = {name: g.copy() for name, g in grids.items()}

    if interp_grids:
        stacked = np.concatenate([g.ravel() for g in interp_grids.values()])
        finite = stacked[np.isfinite(stacked)]
        z_range = (
            (float(finite.min()), float(finite.max()))
            if settings.shared_scale and finite.size
            else None
        )
    else:
        z_range = None

    return Analysis(grids=grids, interp_grids=interp_grids, ref_rms=ref_rms, z_range=z_range)


# --- shared render helpers (frontend-agnostic) -----------------------------

def measured_points(
    grid: np.ndarray,
    hole_data: Mapping[tuple[int, int], object],
) -> tuple[list[tuple[int, int]], list[float]]:
    """Return measured hole positions and their grid values, dropping NaNs.

    Args:
        grid: The sparse band-RMS grid for the plate.
        hole_data: Mapping whose keys are the measured ``(x, y)`` coordinates.

    Returns:
        ``(positions, values)`` aligned lists, excluding holes whose grid value
        is NaN.
    """
    positions: list[tuple[int, int]] = []
    values: list[float] = []
    for (x, y) in hole_data.keys():
        v = float(grid[x, y])
        if not np.isnan(v):
            positions.append((x, y))
            values.append(v)
    return positions, values


def ref_marker(ref_value: float | None, *, normalize: bool) -> float | None:
    """The reference value to display as a marker: 1.0 when normalized, else raw."""
    if ref_value is None:
        return None
    return 1.0 if normalize else ref_value
