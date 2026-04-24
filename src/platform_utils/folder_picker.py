from __future__ import annotations

import importlib
import queue
import subprocess
import sys
import threading

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


def _tk_dialog() -> str | None:
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


def _pick_via_tkinter() -> str | None:
    # Tk() must be created on the thread that owns it. Streamlit runs user code
    # on worker threads, so spawn a dedicated thread and hand the result back
    # via a queue.
    q: queue.Queue[tuple[str, object]] = queue.Queue(maxsize=1)

    def _worker() -> None:
        try:
            q.put(("ok", _tk_dialog()))
        except Exception as e:
            q.put(("err", e))

    t = threading.Thread(target=_worker, daemon=True)
    t.start()
    t.join(timeout=300)
    if t.is_alive():
        return None
    try:
        kind, value = q.get_nowait()
    except queue.Empty:
        return None
    if kind == "err":
        return None
    return value  # type: ignore[return-value]


def pick_folder() -> str | None:
    if sys.platform == "darwin":
        return _pick_via_osascript()
    return _pick_via_tkinter()
