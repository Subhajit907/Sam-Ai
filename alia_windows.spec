# -*- mode: python ; coding: utf-8 -*-
# Windows build spec — run via GitHub Actions on a Windows runner.
# ffplay.exe and ffmpeg.exe must exist in the working directory before
# running PyInstaller (the CI workflow downloads them from BtbN/FFmpeg-Builds).

import sys
from pathlib import Path

block_cipher = None

a = Analysis(
    ['sam.py'],
    pathex=['.'],
    binaries=[
        # FFmpeg binaries for audio playback and WAV conversion (replaces macOS afplay/afconvert)
        ('ffplay.exe', '.'),
        ('ffmpeg.exe', '.'),
    ],
    datas=[
        ('modules/assets', 'modules/assets'),
        ('modules/*.py',   'modules'),
    ],
    hiddenimports=[
        # speech recognition
        'speech_recognition',
        'pyaudio',
        # async / edge-tts
        'asyncio',
        'edge_tts',
        # AI backends
        'openai',
        'ollama',
        # document parsing
        'fitz',
        'docx',
        # image / vision
        'PIL',
        'PIL.Image',
        'PIL.ImageTk',
        'PIL.ImageFilter',
        'cv2',
        # utilities
        'dotenv',
        'pyautogui',
        'yt_dlp',
        # database
        'sqlite3',
        # wake word
        'modules.wakeword',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=['hooks/rthook_windows.py'],
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
    [],
    exclude_binaries=True,
    name='Alia AI',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,          # UPX can trigger Windows Defender false positives
    console=False,      # no CMD window
    icon='modules/assets/alia_icon.ico',
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name='Alia AI',
)
