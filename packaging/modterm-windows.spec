# -*- mode: python ; coding: utf-8 -*-

from pathlib import Path


project_root = Path(SPECPATH).parent
entrypoint = project_root / "src" / "modterm" / "__main__.py"
icon = project_root / "build" / "windows" / "modterm.ico"
version_info = project_root / "build" / "windows" / "version_info.txt"

hidden_imports = [
    "serial.serialwin32",
    "serial.tools.list_ports_windows",
]

analysis = Analysis(
    [str(entrypoint)],
    pathex=[str(project_root / "src")],
    binaries=[],
    datas=[],
    hiddenimports=hidden_imports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=1,
)

pyz = PYZ(analysis.pure)

executable = EXE(
    pyz,
    analysis.scripts,
    analysis.binaries,
    analysis.datas,
    [],
    name="ModTerm",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    icon=str(icon),
    version=str(version_info),
    uac_admin=False,
    uac_uiaccess=False,
)

