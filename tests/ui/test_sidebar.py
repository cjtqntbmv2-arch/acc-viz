from __future__ import annotations

from typing import get_args

from src.ui.sidebar import Axis, Settings


def test_settings_is_frozen():
    s = Settings(folders=[("Platte 1", "/a")], f_min=0, f_max=25000,
                 axis="X", normalize=False, shared_scale=True, colorscale="Viridis")
    try:
        s.f_min = 100  # type: ignore[misc]
    except Exception:
        return
    raise AssertionError("Settings should be frozen")


def test_settings_accepts_multiple_folders():
    s = Settings(folders=[("Platte 1", "/a"), ("Platte 2", "/b")],
                 f_min=0, f_max=100, axis="Y",
                 normalize=True, shared_scale=False, colorscale="Plasma")
    assert len(s.folders) == 2
    assert s.axis == "Y"


def test_settings_accepts_rss_axis():
    s = Settings(folders=[("Platte 1", "/a")], f_min=0, f_max=25000,
                 axis="RSS", normalize=False, shared_scale=True, colorscale="Viridis")
    assert s.axis == "RSS"


def test_settings_interpolate_default_true():
    s = Settings(folders=[("Platte 1", "/a")], f_min=0, f_max=25000,
                 axis="X", normalize=False, shared_scale=True, colorscale="Viridis")
    assert s.interpolate is True


def test_settings_interpolate_can_be_disabled():
    s = Settings(folders=[("Platte 1", "/a")], f_min=0, f_max=25000,
                 axis="X", normalize=False, shared_scale=True,
                 colorscale="Viridis", interpolate=False)
    assert s.interpolate is False


def test_settings_histogram_bins_default_is_20():
    s = Settings(folders=[("Platte 1", "/a")], f_min=0, f_max=25000,
                 axis="X", normalize=False, shared_scale=True, colorscale="Viridis")
    assert s.histogram_bins == 20


def test_settings_histogram_bins_can_be_set():
    s = Settings(folders=[("Platte 1", "/a")], f_min=0, f_max=25000,
                 axis="X", normalize=False, shared_scale=True,
                 colorscale="Viridis", histogram_bins=10)
    assert s.histogram_bins == 10


def test_axis_literal_contains_rss():
    args = get_args(Axis)
    assert "RSS" in args
    assert set(args) == {"X", "Y", "Z", "RSS"}


def test_settings_interp_method_default_is_linear():
    s = Settings(folders=[("Platte 1", "/a")], f_min=0, f_max=25000,
                 axis="X", normalize=False, shared_scale=True, colorscale="Viridis")
    assert s.interp_method == "linear"


def test_settings_interp_method_can_be_tps():
    s = Settings(folders=[("Platte 1", "/a")], f_min=0, f_max=25000,
                 axis="X", normalize=False, shared_scale=True,
                 colorscale="Viridis", interp_method="tps")
    assert s.interp_method == "tps"
