# -*- mode: python ; coding: utf-8 -*-
"""AI Director Windows PyInstaller spec.

Önerilen dağıtım: onedir. Inno Setup bu klasörü kurulum paketi haline getirir.
"""
from PyInstaller.utils.hooks import collect_all, collect_submodules

app_root = r'..'
datas = []
binaries = []
hiddenimports = []

# PySide6 plugin/QML/Qt DLL'lerinin eksik kalmasını önle.
for package in ('PySide6', 'imageio_ffmpeg', 'whisper'):
    d, b, h = collect_all(package)
    datas += d
    binaries += b
    hiddenimports += h

# Uygulamanın lazy-loaded modülleri ve paketleri.
hiddenimports += collect_submodules('app')

# Critical lazy-loaded feature packages: keep these explicit as a second
# packaging guard. The UI imports several of them only when a feature is
# opened, so a successful startup alone is not sufficient validation.
for package in (
    'app.subtitle',
    'app.subtitle.models',
    'app.subtitle.formats',
    'app.subtitle.style',
    'app.subtitle.editor',
    'app.subtitle.embed',
    'app.subtitle.emoji',
    'app.subtitle.typography',
    'app.subtitle.transcribe',
    'app.subtitle.worker',
):
    hiddenimports += collect_submodules(package)

# YouTube is also heavily lazy-loaded. Keep the complete feature package
# explicit so Studio/Analytics/Auto-Publish/Production Manager cannot disappear
# from a frozen build even if import analysis changes.
for package in (
    'app.youtube',
    'app.youtube.client',
    'app.youtube.analytics',
    'app.youtube.publish',
    'app.youtube.creator',
    'app.youtube.dna',
    'app.youtube.studio',
    'app.youtube.thumbnail_render',
    'app.youtube.production_queue',
    'app.youtube.production_manager',
    'app.youtube.manager',
    'app.youtube.health',
    'app.ui.youtube_connection_dialog',
):
    hiddenimports += collect_submodules(package)


a = Analysis(
    ['../app/main.py'],
    pathex=['..'],
    binaries=binaries,
    datas=datas + [
        ('../assets', 'assets'),
    ],
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='AI_Director',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    icon='../assets/AI_Director.ico',
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    name='AI_Director',
)
