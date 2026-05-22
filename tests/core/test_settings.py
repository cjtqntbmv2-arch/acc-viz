from __future__ import annotations

from typing import get_args

from src.core.settings import Axis, Settings


def test_settings_importable_from_core():
    s = Settings(folders=[("Platte 1", "/a")], f_min=0, f_max=25000,
                 axis="X", normalize=False, shared_scale=True, colorscale="Viridis")
    assert s.f_min == 0
    assert s.interpolate is True
    assert s.histogram_bins == 20
    assert s.interp_method == "linear"


def test_settings_is_frozen():
    s = Settings(folders=[("Platte 1", "/a")], f_min=0, f_max=25000,
                 axis="X", normalize=False, shared_scale=True, colorscale="Viridis")
    try:
        s.f_min = 100  # type: ignore[misc]
    except Exception:
        return
    raise AssertionError("Settings should be frozen")


def test_axis_literal_contains_rss():
    assert set(get_args(Axis)) == {"X", "Y", "Z", "RSS"}


def test_sidebar_reexports_core_settings():
    """Backward-compat: src.ui.sidebar must still expose the same Settings/Axis."""
    from src.ui.sidebar import Axis as SidebarAxis
    from src.ui.sidebar import Settings as SidebarSettings

    assert SidebarSettings is Settings
    assert SidebarAxis is Axis
