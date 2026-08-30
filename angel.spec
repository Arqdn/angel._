# -*- mode: python ; coding: utf-8 -*-
# PyInstaller build:  pyinstaller angel.spec  ->  dist/Angel/Angel.exe
# Keep your .env next to Angel.exe (config/ and logs/ are created there too).

from PyInstaller.utils.hooks import collect_submodules

a = Analysis(
    ["app.py"],
    pathex=[],
    binaries=[],
    datas=[
        ("ui", "ui"),
        ("assets", "assets"),
        ("config/defaults.json", "config"),
    ],
    hiddenimports=(
        collect_submodules("faster_whisper")
        + ["sounddevice", "ormsgpack", "mss", "PIL", "psutil",
           "pyautogui", "pycaw", "comtypes"]
    ),
    hookspath=[],
    runtime_hooks=[],
    excludes=["tkinter", "matplotlib"],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="Angel",
    debug=False,
    upx=False,
    console=False,
    icon="assets/angel/icon.ico",
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    upx=False,
    name="Angel",
)
