from __future__ import annotations

"""Frontend-agnostic orchestration of the load → grid → interpolate pipeline.

Frontend-agnostic computation core: the same logic drives the Qt desktop UI
and can be unit-tested without a UI. No Qt imports here on purpose.
"""

import math
from collections import OrderedDict
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import pandas as pd

from src.analysis.grid import build_grid
from src.analysis.interpolation import interpolate_grid
from src.analysis.rms import compute_band_rms
from src.core.settings import Settings
from src.io.plate_loader import LoadResult, count_plate_files, load_plate
from src.io.schema import AccVizError, LoadCancelled, ProgressCallback
from src.logging_setup import get_logger
from src.core import strings as S
from src.core.errors import format_error

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
            otherwise ``None``. Derived from the interpolated grids, so it
            drives the heatmap colour scale.
        hist_range: Shared ``(min, max)`` range for the per-plate histograms,
            derived from the *measured* (sparse) grids only — never from
            interpolated values — so the histogram reflects real measurements.
            ``None`` when :attr:`Settings.shared_scale` is unset or no finite
            measured data exists.
    """

    grids: dict[str, np.ndarray]
    interp_grids: dict[str, np.ndarray]
    ref_rms: dict[str, float]
    z_range: tuple[float, float] | None
    hist_range: tuple[float, float] | None


# --- loading (with mtime-based caching) ------------------------------------

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


def _make_inner(
    progress: ProgressCallback, base: int, grand_total: int
) -> ProgressCallback:
    """Offset a per-folder callback into the global 0..grand_total bar."""
    def inner(i: int, _total: int, name: str) -> None:
        progress(base + i, grand_total, name)

    return inner


def _cached_load(folder: str, *, progress: ProgressCallback | None = None) -> LoadResult:
    """Load a plate folder, memoized (LRU) by (folder, newest-csv-mtime)."""
    token = _folder_mtime_token(folder)
    key = (folder, token)
    cached = _LOAD_CACHE.get(key)
    if cached is not None:
        _LOAD_CACHE.move_to_end(key)
        return cached
    result = load_plate(folder, progress=progress)
    _LOAD_CACHE[key] = result
    if len(_LOAD_CACHE) > _CACHE_MAXSIZE:
        _LOAD_CACHE.popitem(last=False)
    return result


def load_plates(
    folders: Sequence[tuple[str, str]], *, progress: ProgressCallback | None = None
) -> PlateLoad:
    """Load every plate folder, collecting warnings and user-facing errors.

    Each folder is loaded (with mtime-based caching), warnings are prefixed
    with the plate label, and load failures are turned into localized error
    strings instead of raising.

    A single global progress bar spanning 0..grand_total is maintained when
    ``progress`` is provided. ``base`` advances by a folder's full file count
    on every outcome (success OR error), keeping the bar monotonic.

    Args:
        folders: List of ``(label, raw_path)`` tuples.
        progress: Optional callback ``(done, total, name) -> None``.  Raise
            :class:`~src.io.schema.LoadCancelled` inside the callback to abort.

    Returns:
        A :class:`PlateLoad` with the successfully loaded plates plus any
        warnings and errors.
    """
    plates: dict[str, PlateEntry] = {}
    warnings: list[str] = []
    errors: list[str] = []

    # One global progress bar 0..grand_total. Counts are taken once up front so
    # `base` can advance by a folder's full size on EVERY outcome (success OR
    # error), keeping the bar monotonic and always reaching the total. The count
    # is a best-effort snapshot; if a folder's files change mid-load the bar may
    # not land exactly on 100% (QProgressDialog clamps harmlessly).
    counts = (
        [count_plate_files(folder) for _, folder in folders]
        if progress is not None
        else []
    )
    grand_total = sum(counts)
    base = 0

    for idx, (label, folder) in enumerate(folders):
        inner = _make_inner(progress, base, grand_total) if progress is not None else None
        result: LoadResult | None = None
        try:
            result = _cached_load(folder, progress=inner)
        except LoadCancelled:
            raise  # MUST precede the AccVizError/Exception handlers
        except AccVizError as exc:
            _LOG.warning("Plate %s load failed: %s", label, exc)
            errors.append(format_error(exc, plate_label=label))
        except Exception as exc:  # defensive: surface unexpected errors
            _LOG.exception("Unexpected error loading plate %s", label)
            errors.append(S.ERROR_GENERIC_PLATE.format(label=label, detail=str(exc)))
        finally:
            if progress is not None:
                base += counts[idx]

        if result is None:
            continue
        for w in result.warnings:
            warnings.append(f"{label}: {w}")
        plates[label] = (result.hole_data, result.ref_df)

    return PlateLoad(plates=plates, warnings=warnings, errors=errors)


# --- analysis --------------------------------------------------------------

def analyze(plates: dict[str, PlateEntry], settings: Settings) -> Analysis:
    """Compute per-plate grids, reference RMS, interpolation and shared z-range.

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

    # z_range drives the heatmap colour scale (interpolated surface); hist_range
    # drives the histogram x-axis and must stay on real measurements only.
    z_range = _shared_range(interp_grids.values()) if settings.shared_scale else None
    hist_range = _shared_range(grids.values()) if settings.shared_scale else None

    return Analysis(
        grids=grids,
        interp_grids=interp_grids,
        ref_rms=ref_rms,
        z_range=z_range,
        hist_range=hist_range,
    )


def _shared_range(grids: Iterable[np.ndarray]) -> tuple[float, float] | None:
    """Return the ``(min, max)`` over all finite cells, or ``None`` if empty."""
    arrays = list(grids)
    if not arrays:
        return None
    stacked = np.concatenate([g.ravel() for g in arrays])
    finite = stacked[np.isfinite(stacked)]
    if not finite.size:
        return None
    return float(finite.min()), float(finite.max())


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
