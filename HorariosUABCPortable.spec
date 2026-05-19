# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

a = Analysis(
    ['portable_launcher.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('app\\templates', 'app\\templates'),
        ('app\\assets', 'app\\assets'),
    ],
    hiddenimports=[
        'waitress',
        'waitress.server',
        'waitress.task',
        'waitress.channel',
        'sqlalchemy.dialects.sqlite',
        'sqlalchemy.pool',
        'flask_sqlalchemy',
        'flask_migrate',
        'app',
        'app.extensions',
        'app.config',
        'app.models',
        'app.seeds.initial_seed',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['setuptools', 'pkg_resources', '_distutils_hack', 'distutils', 'unittest', 'pydoc', 'doctest'],
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
    name='HorariosUABCPortable',
    debug=False,
    bootloader_ignore_hints=False,
    strip=False,
    upx=True,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='app_icon.ico',
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='HorariosUABCPortable',
)
