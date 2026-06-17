from __future__ import annotations

"""Cross-platform native folder-picker dialog run on a worker thread."""

import importlib
import logging
import queue
import subprocess
import sys
import threading

from src.platform_utils.subprocess_utils import run_hidden

_LOG = logging.getLogger(__name__)

_APPLESCRIPT = (
    'tell application "System Events" to activate\n'
    'set chosenFolder to choose folder with prompt "Ordner wählen"\n'
    'POSIX path of chosenFolder'
)


def _pick_via_osascript() -> str | None:
    """Show a native macOS folder picker via ``osascript`` and return its path."""
    try:
        result = run_hidden(
            ["osascript", "-e", _APPLESCRIPT],
            capture_output=True,
            text=True,
            timeout=300,
        )
    except subprocess.TimeoutExpired:
        _LOG.warning("osascript folder picker timed out")
        return None
    if result.returncode != 0:
        _LOG.info(
            "osascript folder picker cancelled or failed (rc=%s stderr=%s)",
            result.returncode,
            result.stderr,
        )
        return None
    path = (result.stdout or "").strip().rstrip("/")
    return path or None


def _tk_dialog() -> str | None:
    """Open a Tk ``askdirectory`` dialog on the current thread and return its path."""
    tk = importlib.import_module("tkinter")
    fd = importlib.import_module("tkinter.filedialog")
    root = tk.Tk()
    try:
        root.withdraw()
        try:
            root.attributes("-topmost", True)
        except Exception as exc:
            _LOG.debug("tk topmost attribute unavailable: %s", exc)
        path = fd.askdirectory(parent=root)
    finally:
        try:
            root.destroy()
        except Exception as exc:
            _LOG.debug("tk destroy failed: %s", exc)
    return path or None


def _pick_via_tkinter() -> str | None:
    """Run the Tk folder dialog on a dedicated thread and return its result."""
    # Tk() must be created on the thread that owns it, so spawn a dedicated
    # thread and hand the result back
    # via a queue.
    q: queue.Queue[tuple[str, object]] = queue.Queue(maxsize=1)

    def _worker() -> None:
        try:
            q.put(("ok", _tk_dialog()))
        except Exception as exc:
            _LOG.warning("Tkinter folder dialog raised: %s", exc)
            q.put(("err", exc))

    t = threading.Thread(target=_worker, daemon=True)
    t.start()
    t.join(timeout=300)
    if t.is_alive():
        _LOG.warning("Tkinter folder picker timed out")
        return None
    try:
        kind, value = q.get_nowait()
    except queue.Empty:
        return None
    if kind == "err":
        _LOG.warning("Tkinter folder picker error: %s", value)
        return None
    return value  # type: ignore[return-value]


def pick_folder() -> str | None:
    """Show a native folder picker appropriate for the current platform.

    Uses AppleScript on macOS and a Tk dialog elsewhere. The call blocks until
    the dialog is closed or an internal timeout elapses.

    Returns:
        The absolute path selected by the user, or ``None`` when the dialog
        was cancelled, timed out, or failed.
    """
    if sys.platform == "darwin":
        return _pick_via_osascript()
    return _pick_via_tkinter()
