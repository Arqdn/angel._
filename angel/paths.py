"""Central path resolution so every module agrees on where things live."""

from __future__ import annotations

import sys
from pathlib import Path


def project_root() -> Path:
    """Repo root in dev mode; the unpacked folder when frozen by PyInstaller."""
    if getattr(sys, "frozen", False):
        return Path(getattr(sys, "_MEIPASS", Path(sys.executable).parent))
    return Path(__file__).resolve().parent.parent


def writable_root() -> Path:
    """Where runtime files (logs, settings) go. Next to the exe when frozen."""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return project_root()


ROOT = project_root()
CONFIG_DIR = writable_root() / "config"
DEFAULTS_FILE = project_root() / "config" / "defaults.json"
SETTINGS_FILE = CONFIG_DIR / "settings.json"
UI_DIR = ROOT / "ui"
ASSETS_DIR = ROOT / "assets"
LOGS_DIR = writable_root() / "logs"
SCREENSHOTS_DIR = LOGS_DIR / "screenshots"


def ensure_runtime_dirs() -> None:
    for d in (CONFIG_DIR, LOGS_DIR, SCREENSHOTS_DIR):
        d.mkdir(parents=True, exist_ok=True)
