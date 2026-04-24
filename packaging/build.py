from __future__ import annotations

import logging
import os
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
SPEC = ROOT / "packaging" / "acc_viz.spec"
DIST = ROOT / "dist" / "acc_viz"

_LOG = logging.getLogger(__name__)


def _run(cmd: list[str], **kw) -> None:
    _LOG.info("+ %s", " ".join(cmd))
    subprocess.check_call(cmd, cwd=ROOT, **kw)


def _binary_path() -> Path:
    if sys.platform == "darwin":
        return ROOT / "dist" / "acc_viz.app" / "Contents" / "MacOS" / "acc_viz"
    if sys.platform.startswith("win"):
        return DIST / "acc_viz.exe"
    return DIST / "acc_viz"


def _free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def _smoke_test() -> None:
    bin_path = _binary_path()
    if not bin_path.exists():
        raise SystemExit(f"Built binary not found: {bin_path}")

    port = _free_port()
    env = {**os.environ, "ACC_VIZ_PORT": str(port), "ACC_VIZ_OPEN_BROWSER": "0"}
    proc = subprocess.Popen([str(bin_path)], env=env)
    try:
        health = f"http://127.0.0.1:{port}/_stcore/health"
        deadline = time.time() + 60
        last_err: Exception | None = None
        while time.time() < deadline:
            if proc.poll() is not None:
                raise SystemExit(
                    f"Bundled app exited prematurely with code {proc.returncode}"
                )
            try:
                with urllib.request.urlopen(health, timeout=2) as r:
                    if r.status == 200:
                        _LOG.info("Smoke test: health OK on port %s", port)
                        return
            except (urllib.error.URLError, ConnectionError, TimeoutError, OSError) as e:
                last_err = e
                time.sleep(1)
        raise SystemExit(f"Smoke test failed (no health response): {last_err}")
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            proc.kill()


def main() -> None:
    _run([sys.executable, "-m", "PyInstaller", "--noconfirm", str(SPEC)])
    _smoke_test()


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    main()
