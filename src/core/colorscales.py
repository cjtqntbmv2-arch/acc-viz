from __future__ import annotations

"""Canonical colorscale identifiers and their matplotlib colormap equivalents.

Single source of truth shared by the Qt control panel and the matplotlib
heatmap canvas, so the selectable list and the colormap mapping can never
drift apart.
"""

# User-selectable colorscale identifiers, kept stable for continuity with
# saved user expectations.
COLORSCALES: tuple[str, ...] = (
    "Viridis", "Plasma", "Hot", "RdBu", "Cividis", "Turbo", "Inferno",
)

# Colorscale identifier -> matplotlib colormap name.
_COLORSCALE_TO_CMAP: dict[str, str] = {
    "Viridis": "viridis",
    "Plasma": "plasma",
    "Hot": "hot",
    "RdBu": "RdBu",
    "Cividis": "cividis",
    "Turbo": "turbo",
    "Inferno": "inferno",
}


def to_cmap(name: str) -> str:
    """Map a colorscale identifier to a matplotlib colormap name.

    Falls back to ``"viridis"`` for unknown names so rendering never fails.
    """
    return _COLORSCALE_TO_CMAP.get(name, "viridis")
