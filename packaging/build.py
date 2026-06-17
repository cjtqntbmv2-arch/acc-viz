from __future__ import annotations

"""Build the native desktop bundle with PyInstaller and smoke-test the binary.

The smoke test launches the frozen app with ``ACC_VIZ_SMOKE=1`` (which makes it
self-quit after a short delay) on the Qt 'offscreen' platform, then asserts a
clean exit code — no display or human interaction required.
"""

import logging
import os
import subprocess
import sys
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


def _smoke_test() -> None:
    bin_path = _binary_path()
    if not bin_path.exists():
        raise SystemExit(f"Built binary not found: {bin_path}")

    env = {
        **os.environ,
        "ACC_VIZ_SMOKE": "1",
        "QT_QPA_PLATFORM": "offscreen",
    }
    _LOG.info("Smoke test: launching %s (offscreen, self-quit)", bin_path)
    try:
        proc = subprocess.run([str(bin_path)], env=env, timeout=90)
    except subprocess.TimeoutExpired as exc:
        raise SystemExit("Smoke test failed: app did not exit within 90s") from exc

    if proc.returncode != 0:
        raise SystemExit(
            f"Smoke test failed: app exited with code {proc.returncode}"
        )
    _LOG.info("Smoke test passed: clean exit")


def main() -> None:
    _run([sys.executable, "-m", "PyInstaller", "--noconfirm", str(SPEC)])
    _smoke_test()


if __name__ == "__main__":
    # Running as a standalone script puts ``packaging/`` on ``sys.path[0]``,
    # not the repo root, so make ``src`` importable before importing from it.
    sys.path.insert(0, str(ROOT))
    from src.logging_setup import configure_logging

    configure_logging()
    main()
