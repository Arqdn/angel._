"""Settings: defaults.json (committed) deep-merged with settings.json (user, gitignored).

Secrets are NOT stored here — they come from environment variables / .env only.
"""

from __future__ import annotations

import copy
import json
import logging
import os
import threading
from typing import Any

from angel import paths

log = logging.getLogger("angel.settings")


def _deep_merge(base: dict, override: dict) -> dict:
    out = copy.deepcopy(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(out.get(key), dict):
            out[key] = _deep_merge(out[key], value)
        else:
            out[key] = copy.deepcopy(value)
    return out


class Settings:
    """Thread-safe dotted-path access: settings.get('tts.model')."""

    def __init__(self, data: dict[str, Any]):
        self._lock = threading.RLock()
        self._data = data

    @classmethod
    def load(cls) -> "Settings":
        try:
            defaults = json.loads(paths.DEFAULTS_FILE.read_text(encoding="utf-8"))
        except FileNotFoundError:
            log.error("defaults.json missing at %s", paths.DEFAULTS_FILE)
            defaults = {}
        user: dict = {}
        if paths.SETTINGS_FILE.exists():
            try:
                user = json.loads(paths.SETTINGS_FILE.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError) as exc:
                log.warning("settings.json unreadable (%s); using defaults", exc)
        return cls(_deep_merge(defaults, user))

    def get(self, dotted: str, fallback: Any = None) -> Any:
        with self._lock:
            node: Any = self._data
            for part in dotted.split("."):
                if not isinstance(node, dict) or part not in node:
                    return fallback
                node = node[part]
            return copy.deepcopy(node) if isinstance(node, (dict, list)) else node

    def set(self, dotted: str, value: Any) -> None:
        with self._lock:
            node = self._data
            parts = dotted.split(".")
            for part in parts[:-1]:
                node = node.setdefault(part, {})
            node[parts[-1]] = value

    def as_dict(self) -> dict[str, Any]:
        with self._lock:
            return copy.deepcopy(self._data)

    def update_many(self, changes: dict[str, Any]) -> None:
        """Apply {'tts.volume': 0.8, ...} style changes."""
        for dotted, value in changes.items():
            self.set(dotted, value)

    def save(self) -> None:
        """Persist ONLY the user-facing tree (never secrets — none live here)."""
        with self._lock:
            paths.CONFIG_DIR.mkdir(parents=True, exist_ok=True)
            tmp = paths.SETTINGS_FILE.with_suffix(".json.tmp")
            tmp.write_text(
                json.dumps(self._data, indent=2, ensure_ascii=False), encoding="utf-8"
            )
            os.replace(tmp, paths.SETTINGS_FILE)
        log.info("Settings saved to %s", paths.SETTINGS_FILE)


def get_secret(name: str) -> str | None:
    """Secrets come from the environment (python-dotenv loads .env in app.py)."""
    value = os.environ.get(name, "").strip()
    return value or None
