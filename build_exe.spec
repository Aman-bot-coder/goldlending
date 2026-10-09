# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec for Gold & Silver Loan Management System
# Build: pyinstaller build_exe.spec

import sys
from pathlib import Path

block_cipher = None

# Gather all required data files
datas = [
    ('assets', 'assets'),
]

# Hidden imports for SQLAlchemy dialects, PySide6, etc.
hidden_imports = [
    'sqlalchemy.dialects.mysql',
    'sqlalchemy.dialects.mysql.pymysql',
    'pymysql',
    'paramiko',
    'sshtunnel',
    'argon2',
    'argon2._utils',
    'argon2.low_level',
    'cryptography',
    'cryptography.fernet',
    'reportlab',
    'reportlab.lib',
    'reportlab.platypus',
    'reportlab.pdfbase',
    'openpyxl',
    'openpyxl.styles',
    'openpyxl.utils',
    'requests',
    'PySide6.QtCore',
    'PySide6.QtGui',
    'PySide6.QtWidgets',
    'PySide6.QtPrintSupport',
    'babel',
    'pyqtgraph',
    'PIL',
    'PIL.Image',
]

a = Analysis(
    ['main.py'],
    pathex=['.'],
    binaries=[],
    datas=datas,
    hiddenimports=hidden_imports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['tkinter', 'matplotlib', 'numpy', 'scipy', 'pandas'],
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
    name='GoldSilverLoan',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,  # No console window for production
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,
    version_file='version_info.txt',
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='GoldSilverLoan',
)
