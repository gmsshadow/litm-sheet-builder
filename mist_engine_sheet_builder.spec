# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec for the Mist Engine Sheet Builder.

Builds a self-contained executable that needs no separate Python install.
Run it on the OS you want to target (PyInstaller does NOT cross-compile):

    pyinstaller mist_engine_sheet_builder.spec          # -> dist/Mist-Engine-Sheet-Builder/

On Windows the result is dist\\Mist-Engine-Sheet-Builder\\Mist-Engine-Sheet-Builder.exe;
on Linux it's dist/Mist-Engine-Sheet-Builder/Mist-Engine-Sheet-Builder.

Notes
-----
* This produces a ONE-DIR build (a folder you zip and ship), not one-file.
  One-dir starts faster and is far more reliable for WeasyPrint, whose native
  Pango/Cairo/HarfBuzz libraries don't always survive the one-file unpack.
* WeasyPrint's Python data and its dependency chain are pulled in via
  collect_all(); the native shared libraries it loads at runtime must be
  present on the build machine (see PACKAGING.md) so PyInstaller can detect
  and copy them. On Windows that means the GTK runtime DLLs are on PATH when
  you build.
* The characters/ folder is bundled read-only as a seed; at runtime the app
  copies it next to the executable into a writable characters/ library (see
  core/paths.py), so users' saves persist.
"""
from PyInstaller.utils.hooks import collect_all, collect_submodules

datas = [
    ("templates", "templates"),
    ("static", "static"),
    ("characters", "characters"),
]
binaries = []
hiddenimports = collect_submodules("core")

# Pull in WeasyPrint and the libraries it leans on, including their data files
# (fonts, css presets) and any native binaries PyInstaller can resolve.
for pkg in ("weasyprint", "tinycss2", "cssselect2", "pydyf", "pyphen",
            "fontTools", "PIL", "cffi"):
    try:
        d, b, h = collect_all(pkg)
        datas += d
        binaries += b
        hiddenimports += h
    except Exception:
        # A package not present at build time just means that branch of
        # functionality won't be bundled; the build still succeeds.
        pass

block_cipher = None

a = Analysis(
    ["run.py"],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["tkinter", "pytest"],
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
    name="Mist-Engine-Sheet-Builder",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=True,          # keep the console so users can see the URL / close to quit
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="Mist-Engine-Sheet-Builder",
)
