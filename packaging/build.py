from __future__ import annotations

import subprocess
import sys
import time
import urllib.request
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
SPEC = ROOT / "packaging" / "acc_viz.spec"
DIST = ROOT / "dist" / "acc_viz"


def _run(cmd: list[str], **kw) -> None:
    print("+", " ".join(cmd))
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
    proc = subprocess.Popen([str(bin_path)])
    try:
        deadline = time.time() + 30
        last_err: Exception | None = None
        while time.time() < deadline:
            try:
                with urllib.request.urlopen("http://localhost:8501/_stcore/health", timeout=2) as r:
                    if r.status == 200:
                        print("Smoke test: health OK")
                        return
            except Exception as e:
                last_err = e
                time.sleep(1)
        raise SystemExit(f"Smoke test failed: {last_err}")
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
    main()
