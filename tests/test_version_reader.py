from __future__ import annotations

import importlib.util
import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

# Load packaging/version_reader.py by path: it lives in the ``packaging`` dir,
# which clashes with the installed PyPI ``packaging`` distribution, so a plain
# ``import version_reader`` is not statically resolvable here.
_spec = importlib.util.spec_from_file_location(
    "version_reader", REPO_ROOT / "packaging" / "version_reader.py"
)
assert _spec is not None and _spec.loader is not None
version_reader = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(version_reader)


def test_read_version_parses_given_pyproject(tmp_path: Path) -> None:
    pp = tmp_path / "pyproject.toml"
    pp.write_text(
        '[build-system]\nrequires = ["setuptools"]\n\n'
        '[project]\nname = "x"\nversion = "1.2.3"\n'
        'requires-python = ">=3.10"\n',
        encoding="utf-8",
    )
    assert version_reader.read_version(pp) == "1.2.3"


def test_read_version_reads_repo_manifest() -> None:
    # Default path resolves to the real pyproject.toml and looks like semver.
    assert re.fullmatch(r"\d+\.\d+\.\d+", version_reader.read_version())


def test_binary_stem_embeds_version(tmp_path: Path) -> None:
    pp = tmp_path / "pyproject.toml"
    pp.write_text('[project]\nname = "x"\nversion = "9.8.7"\n', encoding="utf-8")
    assert version_reader.binary_stem(pp) == "acc_viz-9.8.7"
