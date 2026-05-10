"""Config module — manages ALIA_MODE and API key in .env"""

import os
from pathlib import Path
from dotenv import load_dotenv

_ENV_PATH = Path(__file__).parent.parent / ".env"


def _reload():
    load_dotenv(_ENV_PATH, override=True)


def get_mode() -> str:
    """Returns 'free', 'openai', or '' if not configured."""
    _reload()
    return os.getenv("ALIA_MODE", "").lower()


def get_openai_key() -> str:
    _reload()
    return os.getenv("OPENAI_API_KEY", "")


def save_config(mode: str, openai_key: str = ""):
    """Write ALIA_MODE (and optionally OPENAI_API_KEY) to .env."""
    lines = []
    if _ENV_PATH.exists():
        lines = _ENV_PATH.read_text().splitlines(keepends=True)

    def _set(key, value, lines):
        for i, line in enumerate(lines):
            if line.startswith(f"{key}="):
                lines[i] = f"{key}={value}\n"
                return lines
        lines.append(f"{key}={value}\n")
        return lines

    lines = _set("ALIA_MODE", mode, lines)
    if openai_key:
        lines = _set("OPENAI_API_KEY", openai_key, lines)

    _ENV_PATH.write_text("".join(lines))
    _reload()


def is_configured() -> bool:
    mode = get_mode()
    if mode == "free":
        return True
    if mode == "openai":
        return bool(get_openai_key())
    return False
