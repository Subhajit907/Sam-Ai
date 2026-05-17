"""
Runtime hook — tells the OS to look for libportaudio inside the .app bundle
before searching system paths. This means users don't need brew install portaudio.
"""
import os
import sys

# When running inside a PyInstaller bundle, _MEIPASS is the temp extraction dir.
# libportaudio.2.dylib is placed there (see binaries in alia.spec).
if hasattr(sys, '_MEIPASS'):
    bundle_dir = sys._MEIPASS
    existing = os.environ.get('DYLD_LIBRARY_PATH', '')
    os.environ['DYLD_LIBRARY_PATH'] = f"{bundle_dir}:{existing}" if existing else bundle_dir
