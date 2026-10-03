# -*- mode: python ; coding: utf-8 -*-
# AI Director - PyInstaller build spec
# Build locally with:  pyinstaller AI_Director.spec
# (GitHub Actions does this automatically, see .github/workflows/build-windows.yml)

import sys
from pathlib import Path

block_cipher = None
ROOT = Path(SPECPATH)

datas = [
    (str(ROOT / "assets"), "assets"),
    (str(ROOT / "models"), "models"),
]
# Only include data dirs that actually exist and are non-empty
datas = [(src, dst) for src, dst in datas if Path(src).exists()]

hiddenimports = [
    "PySide6.QtMultimedia",
    "PySide6.QtMultimediaWidgets",
    "PySide6.QtSvg",
    "numpy",
]

a = Analysis(
    ["app/main.py"],
    pathex=[str(ROOT)],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    cipher=block_cipher,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="AI_Director",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="AI_Director",
)
