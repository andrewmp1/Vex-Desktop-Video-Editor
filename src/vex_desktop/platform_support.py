"""OS seams for Linux and macOS. Keep sys.platform checks here."""

from __future__ import annotations

import json
import os
import shutil
import sys
from pathlib import Path

from platformdirs import user_data_dir

APP_NAME = "Vex"
APP_AUTHOR = "DrewPurdy"
KEYRING_SERVICE = "vex-desktop"
SECRET_GEMINI = "gemini_api_key"
SECRET_ANTHROPIC = "anthropic_api_key"
SECRET_OPENAI = "openai_api_key"
SECRET_PEXELS = "pexels_api_key"


def is_macos() -> bool:
    return sys.platform == "darwin"


def is_linux() -> bool:
    return sys.platform.startswith("linux")


def repo_root() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parents[2]


def data_dir() -> Path:
    path = Path(user_data_dir(APP_NAME, APP_AUTHOR))
    path.mkdir(parents=True, exist_ok=True)
    return path


def projects_dir() -> Path:
    path = data_dir() / "projects"
    path.mkdir(parents=True, exist_ok=True)
    return path


def vex_projects_dir() -> Path:
    """Directory used by the Vex CLI (`~/.video-agent/projects`)."""
    override = os.environ.get("AGENT_PROJECTS_DIR")
    if override:
        return Path(override).expanduser()
    return Path.home() / ".video-agent" / "projects"


def ffmpeg_path() -> str | None:
    for key in ("FFMPEG_BINARY", "IMAGEIO_FFMPEG_EXE", "FFMPEG_PATH"):
        value = os.environ.get(key)
        if value:
            return value
    bundled = Path(sys.executable).resolve().parent / "ffmpeg"
    if bundled.is_file():
        return str(bundled)
    return shutil.which("ffmpeg")


def get_secret(name: str) -> str | None:
    try:
        import keyring

        value = keyring.get_password(KEYRING_SERVICE, name)
        if value:
            return value
    except Exception:
        pass
    store = _secret_file()
    if not store.is_file():
        return None
    try:
        payload = json.loads(store.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    value = payload.get(name)
    return str(value) if value else None


def set_secret(name: str, value: str) -> None:
    try:
        import keyring

        if value:
            keyring.set_password(KEYRING_SERVICE, name, value)
        else:
            try:
                keyring.delete_password(KEYRING_SERVICE, name)
            except Exception:
                pass
        return
    except Exception:
        pass
    store = _secret_file()
    payload: dict[str, str] = {}
    if store.is_file():
        try:
            payload = json.loads(store.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            payload = {}
    if value:
        payload[name] = value
    else:
        payload.pop(name, None)
    store.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    store.chmod(0o600)


def _secret_file() -> Path:
    return data_dir() / "secrets.json"
