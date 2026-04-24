# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec for acc_visualisation.
# Build: pyinstaller packaging/acc_viz.spec

from pathlib import Path
import sys

from PyInstaller.utils.hooks import collect_all, collect_data_files, collect_submodules

block_cipher = None

streamlit_datas, streamlit_bins, streamlit_hidden = collect_all("streamlit")
plotly_datas, plotly_bins, plotly_hidden = collect_all("plotly")
scipy_hidden = collect_submodules("scipy")
pandas_hidden = collect_submodules("pandas")

project_root = Path(SPECPATH).parent.resolve()

added_files = [
    (str(project_root / "app.py"), "."),
    (str(project_root / "src"), "src"),
]
added_files += streamlit_datas + plotly_datas

hidden = [
    "streamlit.web.bootstrap",
    "streamlit.runtime.scriptrunner.magic_funcs",
    "tkinter",
    "tkinter.filedialog",
] + streamlit_hidden + plotly_hidden + scipy_hidden + pandas_hidden

a = Analysis(
    [str(project_root / "packaging" / "entry.py")],
    pathex=[str(project_root)],
    binaries=streamlit_bins + plotly_bins,
    datas=added_files,
    hiddenimports=hidden,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
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
    name="acc_viz",
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
