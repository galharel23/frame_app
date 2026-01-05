# -*- mode: python ; coding: utf-8 -*-

a = Analysis(
    ['app.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('image', 'image'),
        ('screens', 'screens'),
        ('utils', 'utils'),
        ('services', 'services'),
        ('exiftool-13.30_64', 'exiftool-13.30_64'),
    ],
    hiddenimports=[
        'flet', 'PIL', 'json', 'subprocess',
        'services.exif_service',
        'services.json_builders_service',
        'services.srt_service',
        'services.geo_math_service',
        'services.qgis_service',
        'services.full_metadata_service',
        'services.utils_service',
    ],
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
    console=False,
    upx=True,
)
