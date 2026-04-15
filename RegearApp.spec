# -*- mode: python ; coding: utf-8 -*-
"""
RegearApp.spec — Configuración de PyInstaller para compilar RegearApp a .exe
Incluye automáticamente los archivos de datos (CSV) necesarios.

Para compilar:
    pyinstaller RegearApp.spec

Para compilar sin limpiar builds anteriores:
    pyinstaller --clean RegearApp.spec
"""
from PyInstaller.utils.hooks import get_module_file_attribute
import sys
import os

block_cipher = None

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[],  # CSVs van sueltos junto al .exe, no dentro del bundle
    hiddenimports=[
        'tkinter',
        'tkinter.ttk',
        'tkinter.messagebox',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludedimports=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='RegearApp',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,  # --windowed: sin consola
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='icon.ico',  # Ícono de la aplicación
)
