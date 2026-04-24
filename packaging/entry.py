from __future__ import annotations

import logging
import os
import socket
import sys
import threading
import time
import webbrowser
from pathlib import Path


def _free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def _open_browser_delayed(url: str, delay: float = 1.5) -> None:
    time.sleep(delay)
    try:
        webbrowser.open(url)
    except Exception as exc:
        logging.getLogger(__name__).warning("Could not open browser: %s", exc)


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    from streamlit.web import bootstrap

    base = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent.parent))
    app_path = str(base / "app.py")
    os.chdir(base)

    port = (
        int(os.environ["ACC_VIZ_PORT"])
        if "ACC_VIZ_PORT" in os.environ
        else _free_port()
    )
    open_browser = os.environ.get("ACC_VIZ_OPEN_BROWSER", "1") != "0"

    if open_browser:
        threading.Thread(
            target=_open_browser_delayed,
            args=(f"http://localhost:{port}",),
            daemon=True,
        ).start()

    bootstrap.run(
        app_path,
        is_hello=False,
        args=[],
        flag_options={
            "server.headless": True,
            "browser.gatherUsageStats": False,
            "server.port": port,
            "server.address": "127.0.0.1",
        },
    )


if __name__ == "__main__":
    main()
