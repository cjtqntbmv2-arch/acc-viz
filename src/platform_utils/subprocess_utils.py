from __future__ import annotations

import subprocess
import sys
from typing import Any


def run_hidden(args: list[str], **kwargs: Any) -> subprocess.CompletedProcess:
    """Run a subprocess, suppressing the console window on Windows."""
    if sys.platform.startswith("win"):
        kwargs.setdefault("creationflags", getattr(subprocess, "CREATE_NO_WINDOW", 0))
    return subprocess.run(args, **kwargs)
