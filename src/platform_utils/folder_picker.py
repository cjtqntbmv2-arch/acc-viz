from __future__ import annotations

import importlib
import subprocess
import sys

from src.platform_utils.subprocess_utils import run_hidden

_APPLESCRIPT = (
    'tell application "System Events" to activate\n'
    'set chosenFolder to choose folder with prompt "Ordner wählen"\n'
    'POSIX path of chosenFolder'
)


def _pick_via_osascript() -> str | None:
    try:
        result = run_hidden(
            ["osascript", "-e", _APPLESCRIPT],
            capture_output=True,
            text=True,
            timeout=300,
        )
    except subprocess.TimeoutExpired:
        return None
    if result.returncode != 0:
        return None
    path = (result.stdout or "").strip().rstrip("/")
    return path or None


def _pick_via_tkinter() -> str | None:
    tk = importlib.import_module("tkinter")
    fd = importlib.import_module("tkinter.filedialog")
    root = tk.Tk()
    try:
        root.withdraw()
        try:
            root.attributes("-topmost", True)
        except Exception:
            pass
        path = fd.askdirectory(parent=root)
    finally:
        try:
            root.destroy()
        except Exception:
            pass
    return path or None


def pick_folder() -> str | None:
    if sys.platform == "darwin":
        return _pick_via_osascript()
    return _pick_via_tkinter()
