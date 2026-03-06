# bladder_diary.spec
# PyInstaller spec file — bundles NIHdiary(editable).pdf inside the .exe
#
# Run with:  pyinstaller bladder_diary.spec

import os

block_cipher = None

a = Analysis(
    ['bladder_diary.py'],
    pathex=[],
    binaries=[],
    # Bundle the PDF template so it lives inside the .exe
    datas=[('NIHdiary(editable).pdf', '.')],
    hiddenimports=[
        'pandas',
        'pdfrw',
        'tkinter',
        'tkinter.filedialog',
    ],
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
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='BladderDiaryFiller',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    # onefile=True produces a single .exe — no folder needed
    console=True,   # Change to False to hide the console window
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
