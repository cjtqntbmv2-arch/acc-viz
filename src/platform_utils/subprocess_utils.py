from __future__ import annotations

"""Thin subprocess wrappers that hide platform-specific console windows."""

import subprocess
import sys
from typing import Any


def run_hidden(args: list[str], **kwargs: Any) -> subprocess.CompletedProcess:
    """Run a subprocess while suppressing the console window on Windows.

    On Windows, injects ``CREATE_NO_WINDOW`` into ``creationflags`` when the
    caller has not supplied one. On other platforms this behaves identically
    to :func:`subprocess.run`.

    Args:
        args: Command and arguments to execute.
        **kwargs: Additional keyword arguments forwarded to
            :func:`subprocess.run`.

    Returns:
        The :class:`subprocess.CompletedProcess` produced by
        :func:`subprocess.run`.
    """
    if sys.platform.startswith("win"):
        kwargs.setdefault("creationflags", getattr(subprocess, "CREATE_NO_WINDOW", 0))
    return subprocess.run(args, **kwargs)
