# -*- mode: python ; coding: utf-8 -*-
import os
from PyInstaller.utils.hooks import collect_all

datas = [
    ('models', 'models'),
    ('assets', 'assets'),
    ('app', 'app'),
    ('utils', 'utils'),
    ('samples', 'samples'),
    ('web', 'web'),
    ('data/users.json', 'data'),
]
binaries = []
hiddenimports = [
    'sqlite3',
    'PIL._tkinter_finder',
    'reportlab',
    'reportlab.graphics',
    'reportlab.platypus',
    'reportlab.lib',
    'customtkinter',
    'tensorflow',
    'keras',
    'h5py',
    'numpy',
    'unittest',
    'flask',
    'flask_cors',
    'app.auth',
    'app.inference',
    'app.database',
    'app.reports',
    'utils.model_loader',
    'utils.preprocessing',
]

# Collect all resources from customtkinter and reportlab
for pkg in ['customtkinter', 'reportlab']:
    tmp_ret = collect_all(pkg)
    datas += tmp_ret[0]
    binaries += tmp_ret[1]
    hiddenimports += tmp_ret[2]

a = Analysis(
    ['main.py'],
    pathex=['.'],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'torch', 'torchvision', 'torchaudio',
        'IPython', 'jupyter', 'zmq', 'sqlalchemy', 'pyarrow',
        'tkinter.test',
    ],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='Parkinova',
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
    icon='assets/logo.ico' if os.path.exists('assets/logo.ico') else None,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name='Parkinova',
)
