from __future__ import annotations

import math

import numpy as np

from src.core.pipeline import analyze, load_plates
from src.core.settings import Settings


def _settings(folders, **kw) -> Settings:
    base = dict(
        f_min=0, f_max=2, axis="X", normalize=False,
        shared_scale=True, colorscale="Viridis",
    )
    base.update(kw)
    return Settings(folders=folders, **base)


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
