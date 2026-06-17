from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
BUILD_SCRIPT = REPO_ROOT / "packaging" / "build.py"


def test_build_script_resolves_src_when_run_directly(tmp_path: Path) -> None:
    """``python packaging/build.py`` must resolve the ``src`` package.

    Regression for the CI failure ``ModuleNotFoundError: No module named
    'src'``: when the script is invoked directly, ``sys.path[0]`` is the
    ``packaging`` directory rather than the repo root, so ``src`` is not
    importable unless the script puts the repo root on ``sys.path`` itself.

    A stub ``PyInstaller`` package (exiting non-zero) short-circuits the
    actual bundle build right after the import succeeds, keeping the test
    fast and deterministic. We assert only that the ``src`` import resolved.
    """
    stub = tmp_path / "PyInstaller"
    stub.mkdir()
    (stub / "__init__.py").write_text("")
    (stub / "__main__.py").write_text("raise SystemExit(2)\n")

    proc = subprocess.run(
        [sys.executable, str(BUILD_SCRIPT)],
        cwd=str(REPO_ROOT),
        env={**os.environ, "PYTHONPATH": str(tmp_path)},
        capture_output=True,
        text=True,
        timeout=60,
    )

    assert "No module named 'src'" not in proc.stderr, proc.stderr
