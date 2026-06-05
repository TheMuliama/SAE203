# -*- mode: python ; coding: utf-8 -*-

from pathlib import Path


project_root = Path(SPECPATH)
datas = [('assets', 'assets'), ('data/schema_documents_sqlite.sql', 'data')]

for source_dir in [
    project_root / 'data' / 'metadata',
    project_root / 'data' / 'documents',
    project_root / 'data' / 'private',
]:
    if not source_dir.exists():
        continue

    for source in source_dir.rglob('*'):
        if source.is_file():
            destination = source.parent.relative_to(project_root)
            datas.append((str(source), str(destination)))


a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=datas,
    hiddenimports=[],
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
    name='SoweDrop',
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
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='SoweDrop',
)
