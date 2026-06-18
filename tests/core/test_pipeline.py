from __future__ import annotations

import math
from typing import Any

import numpy as np
import pytest

from src.core.pipeline import analyze, load_plates
from src.core.settings import Settings


def _settings(folders, **kw) -> Settings:
    base: dict[str, Any] = dict(
        f_min=0, f_max=2, axis="X", normalize=False,
        shared_scale=True, colorscale="Viridis",
    )
    base.update(kw)
    return Settings(folders=tuple(folders), **base)


# --- load_plates -----------------------------------------------------------

def test_load_plates_loads_valid_folder(tmp_path):
    from tests.core.conftest import make_plate_folder
    folder = make_plate_folder(tmp_path / "p1", {(0, 0): 1e-3, (1, 1): 4e-3})
    out = load_plates([("Platte 1", str(folder))])
    assert "Platte 1" in out.plates
    hole_data, ref_df = out.plates["Platte 1"]
    assert set(hole_data.keys()) == {(0, 0), (1, 1)}
    assert ref_df is None
    assert out.errors == []


def test_load_plates_missing_folder_produces_error(tmp_path):
    out = load_plates([("Platte 1", str(tmp_path / "does_not_exist"))])
    assert out.plates == {}
    assert len(out.errors) == 1
    assert "Platte 1" in out.errors[0] or "existiert nicht" in out.errors[0]


def test_load_plates_warns_when_no_reference(tmp_path):
    from tests.core.conftest import make_plate_folder
    folder = make_plate_folder(tmp_path / "p1", {(0, 0): 1e-3})
    out = load_plates([("Platte 1", str(folder))])
    assert any("Platte 1" in w for w in out.warnings)


def test_load_plates_loads_reference(tmp_path):
    from tests.core.conftest import make_plate_folder
    folder = make_plate_folder(tmp_path / "p1", {(0, 0): 1e-3}, ref_val=1e-3)
    out = load_plates([("Platte 1", str(folder))])
    _, ref_df = out.plates["Platte 1"]
    assert ref_df is not None


# --- analyze ---------------------------------------------------------------

def test_analyze_grid_shape(tmp_path):
    from tests.core.conftest import make_plate_folder
    folder = make_plate_folder(tmp_path / "p1", {(0, 0): 1e-3, (1, 1): 4e-3})
    out = load_plates([("Platte 1", str(folder))])
    res = analyze(out.plates, _settings([("Platte 1", str(folder))]))
    assert res.grids["Platte 1"].shape == (2, 2)


def test_analyze_shared_scale_sets_zrange(tmp_path):
    from tests.core.conftest import make_plate_folder
    folder = make_plate_folder(tmp_path / "p1", {(0, 0): 1e-3, (1, 1): 4e-3})
    out = load_plates([("Platte 1", str(folder))])
    res = analyze(out.plates, _settings([("Platte 1", str(folder))], shared_scale=True))
    assert res.z_range is not None
    lo, hi = res.z_range
    assert lo <= hi


def test_analyze_no_shared_scale_zrange_none(tmp_path):
    from tests.core.conftest import make_plate_folder
    folder = make_plate_folder(tmp_path / "p1", {(0, 0): 1e-3, (1, 1): 4e-3})
    out = load_plates([("Platte 1", str(folder))])
    res = analyze(out.plates, _settings([("Platte 1", str(folder))], shared_scale=False))
    assert res.z_range is None


def test_analyze_hist_range_uses_measured_values(tmp_path):
    from tests.core.conftest import make_plate_folder
    folder = make_plate_folder(tmp_path / "p1", {(0, 0): 1e-3, (1, 1): 4e-3})
    out = load_plates([("Platte 1", str(folder))])
    res = analyze(out.plates, _settings([("Platte 1", str(folder))], shared_scale=True))
    measured = np.concatenate([g.ravel() for g in res.grids.values()])
    measured = measured[np.isfinite(measured)]
    assert res.hist_range == (float(measured.min()), float(measured.max()))


def test_analyze_hist_range_ignores_interpolated_overshoot(tmp_path):
    from tests.core.conftest import make_plate_folder
    # Four small corner holes + a much larger reference. Interpolation injects the
    # reference at the grid center, so the interpolated grid (and z_range) far
    # exceeds the measured maximum — but the histogram range must reflect only
    # the measured holes.
    folder = make_plate_folder(
        tmp_path / "p1",
        {(0, 0): 1e-3, (0, 2): 1e-3, (2, 0): 1e-3, (2, 2): 1e-3},
        ref_val=1.0,
    )
    out = load_plates([("Platte 1", str(folder))])
    res = analyze(
        out.plates,
        _settings([("Platte 1", str(folder))], shared_scale=True, interpolate=True),
    )
    measured = np.concatenate([g.ravel() for g in res.grids.values()])
    measured = measured[np.isfinite(measured)]
    assert res.hist_range == (float(measured.min()), float(measured.max()))
    # The reference anchor pulls z_range above the measured max; hist_range must not follow.
    assert res.z_range is not None
    assert res.hist_range is not None
    assert res.z_range[1] > res.hist_range[1]


def test_analyze_no_shared_scale_hist_range_none(tmp_path):
    from tests.core.conftest import make_plate_folder
    folder = make_plate_folder(tmp_path / "p1", {(0, 0): 1e-3, (1, 1): 4e-3})
    out = load_plates([("Platte 1", str(folder))])
    res = analyze(out.plates, _settings([("Platte 1", str(folder))], shared_scale=False))
    assert res.hist_range is None


def test_analyze_interpolate_false_keeps_nan_gaps(tmp_path):
    from tests.core.conftest import make_plate_folder
    # Two diagonal holes -> off-diagonal cells stay NaN when interpolation is off.
    folder = make_plate_folder(tmp_path / "p1", {(0, 0): 1e-3, (1, 1): 4e-3})
    out = load_plates([("Platte 1", str(folder))])
    res = analyze(out.plates, _settings([("Platte 1", str(folder))], interpolate=False))
    g = res.interp_grids["Platte 1"]
    assert math.isnan(g[0, 1])
    assert math.isnan(g[1, 0])


def test_analyze_interpolate_true_fills_gaps(tmp_path):
    from tests.core.conftest import make_plate_folder
    folder = make_plate_folder(
        tmp_path / "p1",
        {(0, 0): 1e-3, (0, 1): 1e-3, (1, 0): 1e-3, (1, 1): 4e-3},
    )
    out = load_plates([("Platte 1", str(folder))])
    res = analyze(out.plates, _settings([("Platte 1", str(folder))], interpolate=True))
    assert np.isfinite(res.interp_grids["Platte 1"]).all()


def test_analyze_ref_rms_present_with_reference(tmp_path):
    from tests.core.conftest import make_plate_folder
    folder = make_plate_folder(tmp_path / "p1", {(0, 0): 4e-3}, ref_val=1e-3)
    out = load_plates([("Platte 1", str(folder))])
    res = analyze(out.plates, _settings([("Platte 1", str(folder))]))
    assert "Platte 1" in res.ref_rms
    assert res.ref_rms["Platte 1"] > 0


def test_load_plates_propagates_cancellation(tmp_path):
    from tests.core.conftest import make_plate_folder
    from src.io.schema import LoadCancelled

    folder = make_plate_folder(tmp_path / "p1", {(0, 0): 1e-3, (1, 1): 4e-3})

    def cb(done, total, name):
        raise LoadCancelled

    with pytest.raises(LoadCancelled):
        load_plates([("Platte 1", str(folder))], progress=cb)


def test_load_plates_progress_is_one_global_bar_across_folders(tmp_path):
    from tests.core.conftest import make_plate_folder

    f1 = make_plate_folder(tmp_path / "p1", {(0, 0): 1e-3, (1, 1): 4e-3})       # 2 files
    f2 = make_plate_folder(tmp_path / "p2", {(0, 0): 1e-3}, ref_val=1e-3)        # 2 files
    seen: list[tuple[int, int]] = []
    load_plates(
        [("Platte 1", str(f1)), ("Platte 2", str(f2))],
        progress=lambda done, total, name: seen.append((done, total)),
    )
    assert [d for d, _ in seen] == [1, 2, 3, 4]
    assert all(t == 4 for _, t in seen)


def test_load_plates_cache_hit_reports_no_progress(tmp_path):
    from tests.core.conftest import make_plate_folder

    folder = make_plate_folder(tmp_path / "p1", {(0, 0): 1e-3, (1, 1): 4e-3})
    load_plates([("Platte 1", str(folder))])           # warm the LRU
    calls: list[str] = []
    load_plates([("Platte 1", str(folder))], progress=lambda d, t, n: calls.append(n))
    assert calls == []


def test_load_plates_progress_monotonic_when_a_folder_errors(tmp_path):
    from tests.core.conftest import make_plate_folder

    good = make_plate_folder(tmp_path / "p1", {(0, 0): 1e-3, (1, 1): 4e-3})     # 2 files
    bad = tmp_path / "p2"
    bad.mkdir()
    (bad / "x0-y0.csv").write_text("# junk\nFrequenz_Hz,PSD_X_g2Hz\n0.0,1e-3\n1.0,1e-3\n")
    seen: list[tuple[int, int]] = []
    out = load_plates(
        [("Platte 1", str(good)), ("Platte 2", str(bad))],
        progress=lambda d, t, n: seen.append((d, t)),
    )
    dones = [d for d, _ in seen]
    assert dones == [1, 2, 3]                  # monotonic, never backwards
    assert all(t == 3 for _, t in seen)        # grand_total stable
    assert "Platte 2" not in out.plates
    assert len(out.errors) == 1
