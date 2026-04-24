from __future__ import annotations

from src.ui.sidebar import Settings


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
