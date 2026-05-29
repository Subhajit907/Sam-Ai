"""
Centralised path resolution.

When running from source: paths are relative to the project root.
When running inside a PyInstaller .app bundle: the bundle directory is
read-only, so writable files (config, memory DB) go to
~/Library/Application Support/Alia AI/ instead.
"""

import sys
from pathlib import Path


def _app_support_dir() -> Path:
    """Return a writable data directory, creating it if needed."""
    if getattr(sys, "frozen", False):
        # PyInstaller .app bundle — use macOS Application Support
        d = Path.home() / "Library" / "Application Support" / "Alia AI"
    else:
        # Running from source — keep everything in the project root
        d = Path(__file__).parent.parent
    d.mkdir(parents=True, exist_ok=True)
    return d


def env_path() -> Path:
    return _app_support_dir() / ".env"


def memory_dir() -> Path:
    d = _app_support_dir() / "memory"
    d.mkdir(parents=True, exist_ok=True)
    return d
