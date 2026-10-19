# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_data_files, collect_submodules

datas = [
    ('C:/Users/youssef/WirelessFileTransfer-v3.0/desktop-sender/assets', 'assets'),
    ('C:/Users/youssef/WirelessFileTransfer-v3.0/release/AirBeam-v5.0-Receiver.apk', 'release'),
    ('C:/Users/youssef/WirelessFileTransfer-v3.0/release/AirBeam-v2.7-Receiver.apk', 'release'),
    ('C:/Users/youssef/WirelessFileTransfer-v3.0/Fix-AirBeam-Firewall.bat', '.')
]
datas += collect_data_files('tkinterdnd2')

hiddenimports = collect_submodules('tkinterdnd2')

a = Analysis(
    ['C:/Users/youssef/WirelessFileTransfer-v3.0/desktop-sender/sender.py'],
    pathex=[],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='AirBeam',
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
    icon=['C:/Users/youssef/WirelessFileTransfer-v3.0/desktop-sender/assets/airbeam.ico'],
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='AirBeam',
)
