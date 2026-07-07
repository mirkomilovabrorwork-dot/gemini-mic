# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec for "Gemini Mic" — macOS menu-bar app.
# Build (on a macOS runner): pyinstaller GeminiMic.spec

from PyInstaller.utils.hooks import collect_all

block_cipher = None

# Bundle PortAudio (sounddevice) fully, plus the pyobjc frameworks rumps needs.
_sd_datas, _sd_bins, _sd_hidden = collect_all("sounddevice")

a = Analysis(
    ["gemini_mic_mac.py"],
    pathex=[],
    binaries=_sd_bins,
    datas=_sd_datas,
    hiddenimports=_sd_hidden + [
        "rumps",
        "objc",
        "Foundation",
        "AppKit",
        "PyObjCTools",
        "PyObjCTools.AppHelper",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    cipher=block_cipher,
)
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="Gemini Mic",
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
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="Gemini Mic",
)

app = BUNDLE(
    coll,
    name="Gemini Mic.app",
    icon=None,
    bundle_identifier="com.autosmart.geminimic",
    info_plist={
        "CFBundleName": "Gemini Mic",
        "CFBundleDisplayName": "Gemini Mic",
        "CFBundleIdentifier": "com.autosmart.geminimic",
        "CFBundleShortVersionString": "1.0.0",
        "CFBundleVersion": "1.0.0",
        "LSUIElement": True,
        "NSMicrophoneUsageDescription": (
            "Gemini Mic ovozingizni matnga aylantirish uchun mikrofondan "
            "foydalanadi."
        ),
        "NSHighResolutionCapable": True,
    },
)
