# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec for the native PySide6 desktop build of acc_visualisation.
# Build: pyinstaller packaging/acc_viz.spec
#
# Note: cross-compiling is not supported by PyInstaller. Build the Windows .exe
# on Windows and the macOS .app on macOS (see .github/workflows/ci.yml).

from pathlib import Path
import sys

from PyInstaller.utils.hooks import collect_data_files, collect_submodules

block_cipher = None

# matplotlib ships data files (mpl-data: fonts, styles) that must be bundled.
mpl_datas = collect_data_files("matplotlib")
mpl_hidden = collect_submodules("matplotlib.backends")
scipy_hidden = collect_submodules("scipy")
pandas_hidden = collect_submodules("pandas")

project_root = Path(SPECPATH).parent.resolve()

# Stamp the current pyproject version into the executable name (acc_viz-X.Y.Z).
sys.path.insert(0, SPECPATH)
from version_reader import binary_stem

exe_name = binary_stem()

added_files = [
    (str(project_root / "desktop_main.py"), "."),
    (str(project_root / "src"), "src"),
    (str(project_root / "ANLEITUNG_DESKTOP.md"), "."),
]
added_files += mpl_datas

hidden = [
    # PySide6 modules used by the app + the matplotlib Qt backend.
    "PySide6.QtCore",
    "PySide6.QtGui",
    "PySide6.QtWidgets",
    "matplotlib.backends.backend_qtagg",
] + mpl_hidden + scipy_hidden + pandas_hidden

# Keep the bundle lean: exclude GUI/server stacks the native app never imports.
excludes = [
    "tornado",
    "tkinter",
    "PyQt5",
    "PyQt6",
    "IPython",
]

a = Analysis(
    [str(project_root / "packaging" / "entry.py")],
    pathex=[str(project_root)],
    binaries=[],
    datas=added_files,
    hiddenimports=hidden,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=excludes,
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name=exe_name,
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    name="acc_viz",
)

if sys.platform == "darwin":
    app = BUNDLE(
        coll,
        name="acc_viz.app",
        icon=None,
        bundle_identifier="com.acc.visualisation",
        info_plist={
            "NSHighResolutionCapable": True,
            "LSBackgroundOnly": False,
        },
    )
