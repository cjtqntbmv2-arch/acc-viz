from __future__ import annotations

"""Backward-compatibility shim — re-exports everything from src.core.strings.

The canonical module has moved to ``src.core.strings``.  Legacy Streamlit
modules in ``src.ui`` that still import ``from src.ui import strings as S``
continue to work via this shim until they are deleted in Task 2.
"""

from src.core.strings import *  # noqa: F401, F403
