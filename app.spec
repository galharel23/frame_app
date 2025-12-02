# -*- mode: python ; coding: utf-8 -*-

a = Analysis(
    ['app.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('image', 'image'),         # ← תיקיית תמונות!
        ('screens', 'screens'),     # ← אם יש Flet screens
        ('utils', 'utils'),         # ← אם יש פונקציות עזר
        ('exiftool-13.30_64', 'exiftool-13.30_64'),  # ← אם את משתמשת
    ],
    hiddenimports=['flet', 'PIL', 'json', 'subprocess'],
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
    a.binaries,
    a.datas,
    [],
    name='TekenFrame',
    debug=False,
    console=False,   # ← אם תרצי לראות שגיאות, תשימי True
    upx=True,
)
