from __future__ import annotations

"""Single source for the project version, read from ``pyproject.toml``.

Used at *build time only* (PyInstaller spec, ``build.py``, CI) to stamp the
current version into the produced ``.exe`` and ``.zip`` names. The frozen app
does not import this at runtime (``pyproject.toml`` is not bundled).

A regex is used instead of ``tomllib`` so the reader behaves identically on
Python 3.10–3.12 without any extra dependency.
"""

import re
from pathlib import Path

_VERSION_RE = re.compile(r'^version\s*=\s*"([^"]+)"', re.MULTILINE)
_DEFAULT_PYPROJECT = Path(__file__).resolve().parent.parent / "pyproject.toml"


def read_version(pyproject_path: Path | None = None) -> str:
    """Return the ``version = "..."`` value from ``pyproject.toml``."""
    path = pyproject_path or _DEFAULT_PYPROJECT
    match = _VERSION_RE.search(path.read_text(encoding="utf-8"))
    if not match:
        raise SystemExit(f"No version found in {path}")
    return match.group(1)


def binary_stem(pyproject_path: Path | None = None) -> str:
    """File stem for the built executable, e.g. ``acc_viz-0.7.2``."""
    return f"acc_viz-{read_version(pyproject_path)}"


if __name__ == "__main__":
    # ``python packaging/version_reader.py`` prints the bare version — handy
    # for shell/CI use without an inline Python snippet.
    print(read_version())
