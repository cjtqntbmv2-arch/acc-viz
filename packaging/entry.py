from __future__ import annotations

import os
import sys
import threading
import time
import webbrowser
from pathlib import Path


def _open_browser_delayed(url: str, delay: float = 1.5) -> None:
    time.sleep(delay)
    try:
        webbrowser.open(url)
    except Exception:
        pass


def main() -> None:
    from streamlit.web import bootstrap

    base = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent.parent))
    app_path = str(base / "app.py")
    os.chdir(base)

    threading.Thread(
        target=_open_browser_delayed,
        args=("http://localhost:8501",),
        daemon=True,
    ).start()

    bootstrap.run(
        app_path,
        is_hello=False,
        args=[],
        flag_options={
            "server.headless": True,
            "browser.gatherUsageStats": False,
            "server.port": 8501,
        },
    )


if __name__ == "__main__":
    main()
